import hashlib
import os
import threading
import time

import cv2
import numpy as np

from database import get_db, registrar_asistencia_db


class FaceEngine:
    RECOGNITION_THRESHOLD = 0.363
    MIN_RECOGNITION_MARGIN = 0.08
    REQUIRED_CONSECUTIVE_MATCHES = 3
    MATCH_CONFIRMATION_WINDOW_SECONDS = 4

    def __init__(self):
        models_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "models"
        )
        detector_path = os.path.join(
            models_dir, "face_detection_yunet_2023mar.onnx"
        )
        recognizer_path = os.path.join(
            models_dir, "face_recognition_sface_2021dec.onnx"
        )
        for model_path in (detector_path, recognizer_path):
            if not os.path.isfile(model_path):
                raise FileNotFoundError(
                    f"Falta el modelo facial requerido: {model_path}"
                )
        self.face_detector = cv2.FaceDetectorYN_create(
            detector_path, "", (320, 320), 0.7, 0.3, 5000
        )
        self.face_recognizer = cv2.FaceRecognizerSF_create(recognizer_path, "")
        self._model_lock = threading.Lock()
        self.dataset_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "dataset_estudiantes"
        )
        os.makedirs(self.dataset_dir, exist_ok=True)
        self.ultimo_registro = {}
        self._pending_identities = {}
        self._camera_stop_event = threading.Event()
        self.student_embeddings = {}
        self.label_to_student = {}
        self.cargar_dataset_fotos()

    def _detect_faces(self, image):
        height, width = image.shape[:2]
        with self._model_lock:
            self.face_detector.setInputSize((width, height))
            _, faces = self.face_detector.detect(image)
        if faces is None:
            return np.empty((0, 15), dtype=np.float32)
        return faces

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

    def _face_sample(self, image, detection):
        with self._model_lock:
            aligned = self.face_recognizer.alignCrop(image, detection)
            embedding = self.face_recognizer.feature(aligned).reshape(-1)
        norm = np.linalg.norm(embedding)
        if not np.isfinite(norm) or norm == 0:
            raise ValueError("No se pudo calcular la representación facial.")
        return embedding / norm

    def _predict_face(self, sample):
        ranked = sorted(
            (
                (float(np.dot(sample, centroid)), label)
                for label, centroid in self.student_embeddings.items()
            ),
            reverse=True,
        )
        if not ranked:
            return None, -1.0, 0.0

        confidence, label = ranked[0]
        margin = (
            confidence - ranked[1][0]
            if len(ranked) > 1
            else float("inf")
        )
        return label, confidence, margin

    @classmethod
    def _is_confident_match(cls, confidence, margin):
        return (
            confidence >= cls.RECOGNITION_THRESHOLD
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

    def _registrar_asistencia_reconocida(
        self, estudiante_id, materia_id, metodo, ahora
    ):
        registro_key = (estudiante_id, materia_id)
        if ahora - self.ultimo_registro.get(registro_key, 0) <= 10:
            return False, None

        try:
            registrar_asistencia_db(
                estudiante_id,
                materia_id,
                estado="Presente",
                metodo=metodo,
            )
        except ValueError as error:
            return False, error

        self.ultimo_registro[registro_key] = ahora
        return True, None

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
        self.student_embeddings = {}
        self.label_to_student = {}

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

        samples_by_student = {}
        fotos_por_estudiante = {}
        propietario_por_hash = {}
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
                with open(photo_path, "rb") as photo_file:
                    photo_hash = hashlib.sha256(photo_file.read()).digest()
                previous_owner = propietario_por_hash.get(photo_hash)
                if previous_owner is not None:
                    if previous_owner != student_id:
                        raise ValueError(
                            "La misma foto facial está enrolada para más de "
                            f"un estudiante: {filename}"
                        )
                    continue
                propietario_por_hash[photo_hash] = student_id
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
                samples_by_student.setdefault(student_id, []).append(sample)
                self.label_to_student[student_id] = {
                    "id": student_id,
                    "codigo_estudiantil": estudiante["codigo_estudiantil"],
                    "nombre_completo": estudiante["nombre_completo"],
                }

        for student_id, samples in samples_by_student.items():
            centroid = np.mean(samples, axis=0)
            norm = np.linalg.norm(centroid)
            if not np.isfinite(norm) or norm == 0:
                raise ValueError(
                    f"No se pudo crear el modelo facial del estudiante {student_id}."
                )
            self.student_embeddings[student_id] = centroid / norm
        print(
            f"[FACE ENGINE] {len(self.label_to_student)} identidades faciales "
            f"disponibles con {sum(map(len, samples_by_student.values()))} fotos."
        )

    def reconocer_imagen(
        self, image_bytes, materia_id, rotacion=0, session_key="default"
    ):
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

        if not self.student_embeddings:
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
                    "confianza": round(float(confidence * 100), 1),
                    "margen": round(float(margin * 100), 1),
                })
                continue

            student_id = estudiante["id"]
            if not self._confirm_identity(student_id, session_key):
                resultados.append({
                    "estado": "verificando",
                    "confianza": round(float(confidence * 100), 1),
                })
                continue

            registrada, error = self._registrar_asistencia_reconocida(
                student_id,
                materia_id,
                "Facial-Telefono",
                time.time(),
            )
            if error is not None:
                resultados.append({
                    "estado": "fuera_horario",
                    "estudiante_id": student_id,
                    "nombre": estudiante["nombre_completo"],
                    "codigo": estudiante["codigo_estudiantil"],
                    "confianza": round(float(confidence * 100), 1),
                    "asistencia_registrada": False,
                    "mensaje": str(error),
                })
                continue
            resultados.append({
                "estado": "identificado",
                "estudiante_id": student_id,
                "nombre": estudiante["nombre_completo"],
                "codigo": estudiante["codigo_estudiantil"],
                "confianza": round(float(confidence * 100), 1),
                "asistencia": "Presente",
                "registro_nuevo": registrada,
                "asistencia_registrada": True,
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
        for face in faces:
            x, y, width, height = face[:4].astype(int)
            sample = self._face_sample(frame, face)
            identificado = None
            confianza = None
            if self.student_embeddings:
                label, confidence, margin = self._predict_face(sample)
                confianza = float(confidence * 100)
                if self._is_confident_match(confidence, margin):
                    identificado = self.label_to_student.get(label)
                    if identificado and identificado["id"] not in inscritos:
                        identificado = None

            if identificado is not None:
                student_id = identificado["id"]
                registrada, error = self._registrar_asistencia_reconocida(
                    student_id,
                    materia_id,
                    "Facial-Carchito",
                    time.time(),
                )
                if error is not None:
                    etiqueta = (
                        f"Estudiante detectado: "
                        f"{identificado['nombre_completo']}"
                    )
                    detalle = "Fuera de horario; asistencia no registrada"
                    color = (0, 165, 255)
                    resultados.append({
                        "estado": "fuera_horario",
                        "estudiante_id": student_id,
                        "nombre": identificado["nombre_completo"],
                        "codigo": identificado["codigo_estudiantil"],
                        "confianza": round(confianza, 1),
                        "asistencia_registrada": False,
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
                        0.65,
                        color,
                        2,
                    )
                    cv2.putText(
                        frame,
                        detalle,
                        (x, min(y + height + 24, frame.shape[0] - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        2,
                    )
                    continue
                etiqueta = identificado["nombre_completo"]
                color = (0, 255, 0)
                resultados.append({
                    "estudiante_id": student_id,
                    "nombre": etiqueta,
                    "codigo": identificado["codigo_estudiantil"],
                    "confianza": round(confianza, 1),
                    "registro_nuevo": registrada,
                    "asistencia_registrada": True,
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
