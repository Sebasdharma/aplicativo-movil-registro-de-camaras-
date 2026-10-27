import unittest
import threading
from unittest.mock import patch

import cv2
import numpy as np

from face_engine import FaceEngine


class _FakeCollector:
    def getResults(self):
        return ((2, 48.0), (1, 42.0), (1, 45.0), (3, 90.0))


class _FakeRecognizer:
    def predict_collect(self, sample, collector):
        return None


class FaceEngineTests(unittest.TestCase):
    def test_face_sample_variants_cover_camera_resolution_and_lighting(self):
        sample = cv2.getGaussianKernel(200, 40) @ cv2.getGaussianKernel(
            200, 40
        ).T
        sample = (sample * 255 / sample.max()).astype("uint8")

        variants = FaceEngine._face_sample_variants(sample)

        self.assertEqual(len(variants), 18)
        self.assertTrue(all(variant.shape == (200, 200) for variant in variants))
        self.assertTrue((variants[9] == cv2.flip(variants[0], 1)).all())

    def test_predict_face_uses_best_distance_per_student_and_reports_margin(self):
        engine = FaceEngine.__new__(FaceEngine)
        engine.recognizer = _FakeRecognizer()

        with patch(
            "cv2.face.StandardCollector_create",
            return_value=_FakeCollector(),
        ):
            label, confidence, margin = engine._predict_face(None)

        self.assertEqual(label, 1)
        self.assertEqual(confidence, 42.0)
        self.assertEqual(margin, 6.0)

    def test_recognition_requires_a_clear_margin_between_students(self):
        self.assertFalse(FaceEngine._is_confident_match(62.1, 13.0))
        self.assertFalse(FaceEngine._is_confident_match(80.0, 9.7))
        self.assertFalse(FaceEngine._is_confident_match(83.85, 2.9))
        self.assertTrue(FaceEngine._is_confident_match(52.1, 15.7))

    def test_identity_requires_three_consecutive_confident_frames(self):
        engine = FaceEngine.__new__(FaceEngine)
        engine._pending_identities = {}

        self.assertFalse(engine._confirm_identity(7, "phone-a"))
        self.assertFalse(engine._confirm_identity(7, "phone-a"))
        self.assertFalse(engine._confirm_identity(7, "phone-b"))
        self.assertTrue(engine._confirm_identity(7, "phone-a"))

        engine._reset_pending_identity("phone-a")
        self.assertNotIn("phone-a", engine._pending_identities)

    def test_failed_attendance_registration_is_retried_on_next_confirmed_scan(self):
        engine = FaceEngine.__new__(FaceEngine)
        engine.ultimo_registro = {}
        engine._pending_identities = {}
        engine.recognizer = object()
        engine.label_to_student = {
            7: {
                "id": 7,
                "codigo_estudiantil": "REAL-007",
                "nombre_completo": "Estudiante Siete",
            }
        }

        with (
            patch.object(
                engine,
                "_decode_image",
                return_value=np.zeros((100, 100, 3), dtype=np.uint8),
            ),
            patch.object(engine, "_detect_faces", return_value=[(0, 0, 100, 100)]),
            patch.object(engine, "_face_sample", return_value=np.zeros((1, 1))),
            patch.object(engine, "_predict_face", return_value=(7, 40.0, 20.0)),
            patch.object(engine, "_confirm_identity", return_value=True),
            patch.object(FaceEngine, "_estudiantes_inscritos", return_value={7}),
            patch(
                "face_engine.registrar_asistencia_db",
                side_effect=[ValueError("La clase ya superó los 10 minutos."), None],
            ) as register_attendance,
            patch("face_engine.time.time", side_effect=[100.0, 101.0]),
        ):
            rejected, rejected_code = engine.reconocer_imagen(b"image", 1)
            accepted, accepted_code = engine.reconocer_imagen(b"image", 1)

        self.assertEqual(rejected_code, 200)
        self.assertEqual(rejected["rostros"][0]["estado"], "fuera_horario")
        self.assertFalse(rejected["rostros"][0]["asistencia_registrada"])
        self.assertEqual(accepted_code, 200)
        self.assertEqual(accepted["rostros"][0]["estado"], "identificado")
        self.assertTrue(accepted["rostros"][0]["asistencia_registrada"])
        self.assertTrue(accepted["rostros"][0]["registro_nuevo"])
        self.assertEqual(register_attendance.call_count, 2)

    def test_attendance_throttle_is_per_student_and_course(self):
        engine = FaceEngine.__new__(FaceEngine)
        engine.ultimo_registro = {}

        with patch("face_engine.registrar_asistencia_db") as register_attendance:
            first = engine._registrar_asistencia_reconocida(
                7, 1, "Facial-Telefono", 100.0
            )
            repeated = engine._registrar_asistencia_reconocida(
                7, 1, "Facial-Telefono", 105.0
            )
            other_course = engine._registrar_asistencia_reconocida(
                7, 2, "Facial-Telefono", 105.0
            )

        self.assertEqual(first, (True, None))
        self.assertEqual(repeated, (False, None))
        self.assertEqual(other_course, (True, None))
        self.assertEqual(register_attendance.call_count, 2)

    def test_stop_live_camera_sets_stop_event(self):
        engine = FaceEngine.__new__(FaceEngine)
        engine._camera_stop_event = threading.Event()

        engine.detener_camara_en_vivo()

        self.assertTrue(engine._camera_stop_event.is_set())


if __name__ == "__main__":
    unittest.main()
