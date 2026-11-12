import hashlib
import os
import threading
import time

import cv2
import numpy as np

from database import get_db, registrar_asistencia_db


class FaceEngine:
    RECOGNITION_THRESHOLD = 0.32
    MIN_RECOGNITION_MARGIN = 0.05
    REQUIRED_CONSECUTIVE_MATCHES = 1
    MATCH_CONFIRMATION_WINDOW_SECONDS = 5

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
            detector_path, "", (320, 320), 0.5, 0.3, 5000
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

    @staticmethod
    def _normalizar_iluminacion(image):
        """
        Normaliza variaciones de luz (poca luz, sombras intensas, contraluz)
        usando CLAHE sobre el canal de luminosidad (L) en espacio LAB.
        """
        if image is None or image.size == 0:
            return image
        try:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            merged = cv2.merge((cl, a, b))
            return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        except Exception:
            return image

    @staticmethod
    def _limitar_resolucion(image, max_dim=720):
        if image is None or image.size == 0:
            return image
        height, width = image.shape[:2]
        largest = max(height, width)
        if largest <= max_dim:
            return image
        scale = max_dim / float(largest)
        return cv2.resize(
            image,
            (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
            interpolation=cv2.INTER_AREA,
        )

    def _decode_image(self, image_bytes):
        image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None or image.size == 0:
            return None
        return self._limitar_resolucion(image)

    def _face_sample(self, image, detection):
        with self._model_lock:
            aligned = self.face_recognizer.alignCrop(image, detection)
            embedding_raw = self.face_recognizer.feature(aligned).reshape(-1)
            norm_raw = np.linalg.norm(embedding_raw)
            if norm_raw > 0 and np.isfinite(norm_raw):
                embedding_raw = embedding_raw / norm_raw

            aligned_flip = cv2.flip(aligned, 1)
            embedding_flip = self.face_recognizer.feature(aligned_flip).reshape(-1)
            norm_flip = np.linalg.norm(embedding_flip)
            if norm_flip > 0 and np.isfinite(norm_flip):
                embedding_flip = embedding_flip / norm_flip

            aligned_norm = self._normalizar_iluminacion(aligned)
            embedding_norm = self.face_recognizer.feature(aligned_norm).reshape(-1)
            norm_norm = np.linalg.norm(embedding_norm)
            if norm_norm > 0 and np.isfinite(norm_norm):
                embedding_norm = embedding_norm / norm_norm

        embedding = 0.4 * embedding_raw + 0.3 * embedding_flip + 0.3 * embedding_norm
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

            missing_names = set()
            for estudiante in estudiantes:
                for fn in (estudiante["foto_legacy"], estudiante["foto_adicional"]):
                    if fn:
                        safe_name = os.path.basename(fn)
                        if safe_name and not os.path.isfile(os.path.join(self.dataset_dir, safe_name)):
                            missing_names.add(safe_name)

            if missing_names:
                placeholders = ",".join("?" for _ in missing_names)
                try:
                    rows_bin = conn.execute(
                        f"""
                        SELECT foto_path, imagen_bytes
                        FROM fotos_faciales_estudiantes
                        WHERE imagen_bytes IS NOT NULL
                          AND foto_path IN ({placeholders})
                        """,
                        tuple(sorted(missing_names)),
                    ).fetchall()
                except Exception:
                    rows_bin = []
                if rows_bin:
                    os.makedirs(self.dataset_dir, exist_ok=True)
                for row_bin in rows_bin:
                    raw = row_bin["imagen_bytes"]
                    if not raw:
                        continue
                    safe_name = os.path.basename(row_bin["foto_path"])
                    target_path = os.path.join(self.dataset_dir, safe_name)
                    if not os.path.isfile(target_path):
                        with open(target_path, "wb") as out_file:
                            out_file.write(bytes(raw))
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
                image = self._limitar_resolucion(image)
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

    @staticmethod
    def _is_face_upright(bounds):
        try:
            if len(bounds) < 14:
                return True
        except TypeError:
            return True
        right_eye_x, right_eye_y = float(bounds[4]), float(bounds[5])
        left_eye_x, left_eye_y = float(bounds[6]), float(bounds[7])
        right_mouth_y, left_mouth_y = float(bounds[11]), float(bounds[13])
        eye_y = 0.5 * (right_eye_y + left_eye_y)
        mouth_y = 0.5 * (right_mouth_y + left_mouth_y)
        dx_eyes = abs(right_eye_x - left_eye_x)
        dy_eyes = abs(right_eye_y - left_eye_y)
        return eye_y < mouth_y and dx_eyes >= dy_eyes * 0.8

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
        needs_orientation_search = (
            len(faces) == 0
            or (len(faces) == 1 and not self._is_face_upright(faces[0]))
        )
        if needs_orientation_search:
            best_image, best_faces = None, None
            candidates = [image]
            if len(faces) == 0:
                candidates.append(self._normalizar_iluminacion(image))
            for base_img in candidates:
                for flag in (
                    None,
                    cv2.ROTATE_180,
                    cv2.ROTATE_90_CLOCKWISE,
                    cv2.ROTATE_90_COUNTERCLOCKWISE,
                ):
                    cand = base_img if flag is None else cv2.rotate(base_img, flag)
                    cand_faces = self._detect_faces(cand)
                    if len(cand_faces) == 1 and self._is_face_upright(cand_faces[0]):
                        best_image, best_faces = cand, cand_faces
                        break
                    if best_faces is None and len(cand_faces) > 0:
                        best_image, best_faces = cand, cand_faces
                if best_faces is not None and len(best_faces) == 1 and self._is_face_upright(best_faces[0]):
                    break
            if best_faces is None:
                flipped = cv2.flip(image, 1)
                for flag in (
                    None,
                    cv2.ROTATE_180,
                    cv2.ROTATE_90_CLOCKWISE,
                    cv2.ROTATE_90_COUNTERCLOCKWISE,
                ):
                    cand = flipped if flag is None else cv2.rotate(flipped, flag)
                    cand_faces = self._detect_faces(cand)
                    if len(cand_faces) == 1 and self._is_face_upright(cand_faces[0]):
                        best_image, best_faces = cand, cand_faces
                        break
                    if best_faces is None and len(cand_faces) > 0:
                        best_image, best_faces = cand, cand_faces
            if best_faces is not None:
                image, faces = best_image, best_faces

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
            is_match = (
                estudiante is not None
                and estudiante["id"] in inscritos
                and self._is_confident_match(confidence, margin)
            )
            if not is_match:
                retry_candidates = (
                    self._normalizar_iluminacion(image),
                    cv2.rotate(image, cv2.ROTATE_180),
                    cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE),
                    cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE),
                    cv2.rotate(self._normalizar_iluminacion(image), cv2.ROTATE_180),
                )
                for cand_img in retry_candidates:
                    cand_faces = self._detect_faces(cand_img)
                    if len(cand_faces) == 1 and self._is_face_upright(cand_faces[0]):
                        cand_sample = self._face_sample(cand_img, cand_faces[0])
                        c_label, c_conf, c_margin = self._predict_face(cand_sample)
                        c_est = self.label_to_student.get(c_label)
                        if (
                            c_est is not None
                            and c_est["id"] in inscritos
                            and self._is_confident_match(c_conf, c_margin)
                        ):
                            label, confidence, margin = c_label, c_conf, c_margin
                            estudiante = c_est
                            is_match = True
                            break
            print(
                f"[FACE SCAN] Match={is_match} | conf={confidence:.3f} | margin={margin:.3f} | "
                f"estudiante={estudiante['nombre_completo'] if estudiante else 'Desconocido'}",
                flush=True,
            )
            if not is_match:
                resultados.append({
                    "estado": "desconocido",
                    "confianza": round(float(confidence * 100), 1),
                    "margen": round(float(margin * 100), 1),
                })
                continue

            student_id = estudiante["id"]
            if not self._confirm_identity(student_id, session_key):
                pending_info = self._pending_identities.get(session_key, (student_id, 1, 0))
                resultados.append({
                    "estado": "verificando",
                    "nombre": estudiante["nombre_completo"],
                    "codigo": estudiante["codigo_estudiantil"],
                    "confianza": round(float(confidence * 100), 1),
                    "confirmaciones": pending_info[1],
                    "requeridas": self.REQUIRED_CONSECUTIVE_MATCHES,
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
