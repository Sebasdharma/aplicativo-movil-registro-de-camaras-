import os
import threading
import time

import cv2
import numpy as np

from database import get_db, registrar_asistencia_db


class FaceEngine:
    RECOGNITION_THRESHOLD = 60.0
    MIN_RECOGNITION_MARGIN = 12.0
    REQUIRED_CONSECUTIVE_MATCHES = 3
    MATCH_CONFIRMATION_WINDOW_SECONDS = 4

    def __init__(self):
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        profile_cascade_path = cv2.data.haarcascades + "haarcascade_profileface.xml"
        self.profile_face_cascade = cv2.CascadeClassifier(profile_cascade_path)
        self.dataset_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "dataset_estudiantes"
        )
        os.makedirs(self.dataset_dir, exist_ok=True)
        self.ultimo_registro = {}
        self._pending_identities = {}
        self._camera_stop_event = threading.Event()
        self.recognizer = None
        self.label_to_student = {}
        self.cargar_dataset_fotos()

    def _detect_faces(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        frontal_faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80)
        )
        if len(frontal_faces) > 0:
            return frontal_faces

        profile_faces = list(self.profile_face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=4, minSize=(80, 80)
        ))
        mirrored_faces = self.profile_face_cascade.detectMultiScale(
            cv2.flip(gray, 1),
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(80, 80),
        )
        for x, y, width, height in mirrored_faces:
            profile_faces.append((gray.shape[1] - x - width, y, width, height))

        unique_faces = []
        for face in sorted(
            profile_faces,
            key=lambda bounds: bounds[2] * bounds[3],
            reverse=True,
        ):
            x, y, width, height = face
            area = width * height
            duplicate = False
            for other_x, other_y, other_width, other_height in unique_faces:
                intersection_width = max(
                    0, min(x + width, other_x + other_width) - max(x, other_x)
                )
                intersection_height = max(
                    0, min(y + height, other_y + other_height) - max(y, other_y)
                )
                intersection = intersection_width * intersection_height
                if intersection / min(
                    area, other_width * other_height
                ) >= 0.5:
                    duplicate = True
                    break
            if not duplicate:
                unique_faces.append(face)
        return np.asarray(unique_faces, dtype=np.int32).reshape(-1, 4)

    def validar_foto_enrolamiento(self, image_bytes):
        image = self._decode_image(image_bytes)
        if image is None:
            return False, "La imagen no es válida."
        faces = self._detect_faces(image)
        if len(faces) != 1:
            return False, "La foto debe mostrar exactamente un rostro."
        return True, ""

    def _decode_image(self, image_bytes):
        image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None or image.size == 0:
            return None
        return image

    def _face_sample(self, image, bounds):
        x, y, width, height = bounds
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        face = gray[y : y + height, x : x + width]
        return cv2.resize(face, (200, 200), interpolation=cv2.INTER_CUBIC)

    @staticmethod
    def _face_sample_variants(sample):
        variants = [sample]
        for size in (80, 110, 140):
            reduced = cv2.resize(sample, (size, size), interpolation=cv2.INTER_AREA)
            variants.append(
                cv2.resize(reduced, (200, 200), interpolation=cv2.INTER_CUBIC)
            )

        values = np.arange(256, dtype=np.float32) / 255
        for gamma in (0.65, 0.8, 1.25, 1.5):
            lookup = np.clip(np.power(values, gamma) * 255, 0, 255).astype(np.uint8)
            variants.append(cv2.LUT(sample, lookup))

        variants.append(
            cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(sample)
        )
        variants.extend(cv2.flip(variant, 1) for variant in list(variants))
        return variants

    def _predict_face(self, sample):
        collector = cv2.face.StandardCollector_create()
        self.recognizer.predict_collect(sample, collector)

        best_distance_by_student = {}
        for label, distance in collector.getResults():
            best_distance_by_student[label] = min(
                distance,
                best_distance_by_student.get(label, float("inf")),
            )
        ranked = sorted(
            best_distance_by_student.items(),
            key=lambda result: result[1],
        )
        if not ranked:
            return None, float("inf"), 0.0

        label, confidence = ranked[0]
        margin = (
            ranked[1][1] - confidence
            if len(ranked) > 1
            else float("inf")
        )
        return label, confidence, margin

    @classmethod
    def _is_confident_match(cls, confidence, margin):
        return (
            confidence <= cls.RECOGNITION_THRESHOLD
            and margin >= cls.MIN_RECOGNITION_MARGIN
        )

    def _confirm_identity(self, student_id, session_key="default"):
        now = time.monotonic()
        self._pending_identities = {
            key: value
            for key, value in self._pending_identities.items()
            if now - value[2] <= self.MATCH_CONFIRMATION_WINDOW_SECONDS
        }
        pending = self._pending_identities.get(session_key)
        if pending is None or pending[0] != student_id:
            count = 1
        else:
            count = pending[1] + 1
        self._pending_identities[session_key] = (student_id, count, now)
        return count >= self.REQUIRED_CONSECUTIVE_MATCHES

    def _reset_pending_identity(self, session_key="default"):
        self._pending_identities.pop(session_key, None)

    @staticmethod
    def _estudiantes_inscritos(materia_id):
        conn = get_db()
        try:
            return {
                row["estudiante_id"]
                for row in conn.execute(
                    """
                    SELECT me.estudiante_id
                    FROM materia_estudiantes me
                    JOIN estudiantes e ON e.id = me.estudiante_id
                    WHERE me.materia_id = ? AND e.activo = 1
                    """,
                    (materia_id,),
                ).fetchall()
            }
        finally:
            conn.close()

    def cargar_dataset_fotos(self):
        self._pending_identities.clear()
        self.recognizer = None
        self.label_to_student = {}

        if not hasattr(cv2, "face") or not hasattr(cv2.face, "LBPHFaceRecognizer_create"):
            print("[FACE ENGINE] Instala opencv-contrib-python para habilitar reconocimiento.")
            return

        conn = get_db()
        try:
            estudiantes = conn.execute(
                """
                SELECT e.id, e.codigo_estudiantil, e.nombre_completo,
                       e.foto_path AS foto_legacy, f.foto_path AS foto_adicional
                FROM estudiantes e
                LEFT JOIN fotos_faciales_estudiantes f ON f.estudiante_id = e.id
                WHERE e.activo = 1
                ORDER BY e.id, f.id
                """
            ).fetchall()
        finally:
            conn.close()

        samples = []
        labels = []
        fotos_por_estudiante = {}
        for estudiante in estudiantes:
            student_id = estudiante["id"]
            fotos = fotos_por_estudiante.setdefault(student_id, set())
            foto_paths = (
                estudiante["foto_legacy"],
                estudiante["foto_adicional"],
            )
            if not any(foto_paths):
                foto_paths = (f"{estudiante['codigo_estudiantil']}.jpg",)
            for filename in foto_paths:
                if not filename or filename in fotos:
                    continue
                fotos.add(filename)
                photo_path = os.path.join(
                    self.dataset_dir, os.path.basename(filename)
                )
                if not os.path.isfile(photo_path):
                    continue
                image = cv2.imread(photo_path)
                if image is None:
                    print(
                        "[FACE ENGINE] No se pudo leer la foto de "
                        f"{estudiante['codigo_estudiantil']}."
                    )
                    continue
                faces = self._detect_faces(image)
                if len(faces) != 1:
                    print(
                        "[FACE ENGINE] Foto omitida: se esperaba un rostro para "
                        f"{estudiante['codigo_estudiantil']}."
                    )
                    continue
                sample = self._face_sample(image, faces[0])
                face_variants = self._face_sample_variants(sample)
                samples.extend(face_variants)
                labels.extend([student_id] * len(face_variants))
                self.label_to_student[student_id] = {
                    "id": student_id,
                    "codigo_estudiantil": estudiante["codigo_estudiantil"],
                    "nombre_completo": estudiante["nombre_completo"],
                }

        if samples:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            self.recognizer.train(samples, np.asarray(labels, dtype=np.int32))
        print(
            f"[FACE ENGINE] {len(self.label_to_student)} identidades faciales disponibles."
        )

    def reconocer_imagen(
        self, image_bytes, materia_id, rotacion=0, session_key="default"
    ):
        if not hasattr(cv2, "face") or not hasattr(cv2.face, "LBPHFaceRecognizer_create"):
            return {
                "status": "error",
                "mensaje": "El backend requiere opencv-contrib-python para reconocer rostros.",
            }, 503

        image = self._decode_image(image_bytes)
        if image is None:
            return {"status": "error", "mensaje": "La imagen recibida no es válida."}, 400
        if rotacion == 90:
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif rotacion == 180:
            image = cv2.rotate(image, cv2.ROTATE_180)
        elif rotacion == 270:
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

        faces = self._detect_faces(image)
        if len(faces) == 0:
            self._reset_pending_identity(session_key)
            return {
                "status": "ok",
                "mensaje": "No se detectó ningún rostro. Intenta con mejor iluminación y enfoca una sola persona.",
                "rostros": [],
            }, 200

        if self.recognizer is None:
            self._reset_pending_identity(session_key)
            return {
                "status": "ok",
                "mensaje": "Se detectó el rostro, pero aún no hay estudiantes con foto biométrica enrolada.",
                "rostros": [
                    {"estado": "desconocido", "mensaje": "Estudiante sin foto enrolada."}
                    for _ in faces
                ],
            }, 200

        inscritos = self._estudiantes_inscritos(materia_id)
        if len(faces) != 1:
            self._reset_pending_identity(session_key)
            return {
                "status": "ok",
                "mensaje": "Mantén una sola persona frente a la cámara para confirmar la identidad.",
                "rostros": [
                    {"estado": "desconocido", "mensaje": "Se requiere un solo rostro."}
                    for _ in faces
                ],
            }, 200

        resultados = []
        for bounds in faces:
            sample = self._face_sample(image, bounds)
            label, confidence, margin = self._predict_face(sample)
            estudiante = self.label_to_student.get(label)
            if (
                estudiante is None
                or estudiante["id"] not in inscritos
                or not self._is_confident_match(confidence, margin)
            ):
                self._reset_pending_identity(session_key)
                resultados.append({
                    "estado": "desconocido",
                    "confianza": round(float(confidence), 1),
                    "margen": round(float(margin), 1),
                })
                continue

            student_id = estudiante["id"]
            if not self._confirm_identity(student_id, session_key):
                resultados.append({
                    "estado": "verificando",
                    "confianza": round(float(confidence), 1),
                })
                continue

            ahora = time.time()
            registrada = ahora - self.ultimo_registro.get(student_id, 0) > 10
            if registrada:
                try:
                    registrar_asistencia_db(
                        student_id,
                        materia_id,
                        estado="Presente",
                        metodo="Facial-Telefono",
                    )
                except ValueError as error:
                    self.ultimo_registro[student_id] = ahora
                    resultados.append({
                        "estado": "fuera_horario",
                        "estudiante_id": student_id,
                        "nombre": estudiante["nombre_completo"],
                        "codigo": estudiante["codigo_estudiantil"],
                        "confianza": round(float(confidence), 1),
                        "mensaje": str(error),
                    })
                    continue
                self.ultimo_registro[student_id] = ahora
            resultados.append({
                "estado": "identificado",
                "estudiante_id": student_id,
                "nombre": estudiante["nombre_completo"],
                "codigo": estudiante["codigo_estudiantil"],
                "confianza": round(float(confidence), 1),
                "asistencia": "Presente",
                "registro_nuevo": registrada,
            })

        identificados = sum(r["estado"] == "identificado" for r in resultados)
        fuera_horario = next(
            (r for r in resultados if r["estado"] == "fuera_horario"),
            None,
        )
        mensaje = (
            f"Se identificaron y registraron {identificados} estudiante(s)."
            if identificados
            else fuera_horario["mensaje"]
            if fuera_horario
            else "Se detectaron rostros, pero ninguno coincidió con suficiente confianza."
        )
        return {"status": "ok", "mensaje": mensaje, "rostros": resultados}, 200

    def procesar_frame(self, frame, materia_id=1):
        faces = self._detect_faces(frame)
        resultados = []
        inscritos = self._estudiantes_inscritos(materia_id)
        for x, y, width, height in faces:
            sample = self._face_sample(frame, (x, y, width, height))
            identificado = None
            confianza = None
            if self.recognizer is not None:
                label, confidence, margin = self._predict_face(sample)
                confianza = float(confidence)
                if self._is_confident_match(confidence, margin):
                    identificado = self.label_to_student.get(label)
                    if identificado and identificado["id"] not in inscritos:
                        identificado = None

            if identificado is not None:
                student_id = identificado["id"]
                ahora = time.time()
                if ahora - self.ultimo_registro.get(student_id, 0) > 10:
                    try:
                        registrar_asistencia_db(
                            student_id,
                            materia_id,
                            estado="Presente",
                            metodo="Facial-Carchito",
                        )
                    except ValueError as error:
                        self.ultimo_registro[student_id] = ahora
                        etiqueta = f"Fuera de horario: {error}"
                        color = (0, 165, 255)
                        resultados.append({
                            "estudiante_id": student_id,
                            "nombre": identificado["nombre_completo"],
                            "codigo": identificado["codigo_estudiantil"],
                            "mensaje": str(error),
                        })
                        cv2.rectangle(
                            frame, (x, y), (x + width, y + height), color, 2
                        )
                        cv2.putText(
                            frame,
                            etiqueta,
                            (x, max(y - 10, 15)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            color,
                            2,
                        )
                        continue
                    self.ultimo_registro[student_id] = ahora
                etiqueta = identificado["nombre_completo"]
                color = (0, 255, 0)
                resultados.append({
                    "estudiante_id": student_id,
                    "nombre": etiqueta,
                    "codigo": identificado["codigo_estudiantil"],
                    "confianza": round(confianza, 1),
                })
            else:
                etiqueta = "Desconocido"
                color = (0, 165, 255)

            cv2.rectangle(frame, (x, y), (x + width, y + height), color, 2)
            cv2.putText(
                frame, etiqueta, (x, max(y - 10, 15)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2,
            )
        return frame, resultados

    def ejecutar_camara_en_vivo(self, materia_id=1):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("No se pudo acceder a la cámara web del dispositivo.")
            return
        print("Escaneo facial AsisTech activado. Presiona 'q' para cerrar la ventana.")
        try:
            while not self._camera_stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    break
                frame_proc, _ = self.procesar_frame(frame, materia_id)
                cv2.imshow(
                    "AsisTech - Reconocimiento Facial en Vivo (UPEC)", frame_proc
                )
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self._camera_stop_event.set()

    def detener_camara_en_vivo(self):
        self._camera_stop_event.set()


if __name__ == "__main__":
    from database import init_db

    init_db()
    engine = FaceEngine()
    engine.ejecutar_camara_en_vivo()
