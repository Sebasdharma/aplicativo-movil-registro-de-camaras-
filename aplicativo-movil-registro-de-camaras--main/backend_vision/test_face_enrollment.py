import base64
import os
import threading
import tempfile
import unittest
from unittest.mock import Mock
from unittest.mock import patch

import cv2
import numpy as np

import database
import server
from face_engine import FaceEngine


class FaceEnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path_patch = patch.object(
            database, "DB_PATH", os.path.join(self.temp_dir.name, "test.db")
        )
        self.db_path_patch.start()
        self.dataset_dir = os.path.join(self.temp_dir.name, "faces")
        os.makedirs(self.dataset_dir)
        self.dataset_patch = patch.object(
            server.face_engine, "dataset_dir", self.dataset_dir
        )
        self.dataset_patch.start()
        self.dataset_reload_patch = patch.object(
            server.face_engine, "cargar_dataset_fotos"
        )
        self.dataset_reload_patch.start()
        self.validation_patch = patch.object(
            server.face_engine,
            "validar_foto_enrolamiento",
            return_value=(True, ""),
        )
        self.validation_patch.start()
        self.client = server.app.test_client()
        database.init_db()
        success, encoded = cv2.imencode(
            ".jpg", np.zeros((120, 120, 3), dtype=np.uint8)
        )
        self.assertTrue(success)
        self.photo = base64.b64encode(encoded).decode("ascii")

    def tearDown(self):
        self.validation_patch.stop()
        self.dataset_reload_patch.stop()
        self.dataset_patch.stop()
        self.db_path_patch.stop()
        self.temp_dir.cleanup()

    def _enroll(self, code, photos, consent=True):
        return self.client.post(
            "/api/estudiantes/enrolar",
            json={
                "codigo": code,
                "nombre": "Estudiante de prueba",
                "paralelo": "Séptimo A - Mañana",
                "email": "",
                "materia_id": 1,
                "fotos": photos,
                "consentimiento_biometrico": consent,
            },
        )

    def test_multiple_authorized_photos_are_preserved_up_to_ten_in_batches(self):
        first = self._enroll("TEST-FACE-001", [self.photo] * 5)
        self.assertEqual(first.status_code, 200, first.json)

        engine = FaceEngine.__new__(FaceEngine)
        engine.dataset_dir = self.dataset_dir
        engine._pending_identities = {}
        engine.student_embeddings = {}
        engine.label_to_student = {}
        sample = np.asarray([1.0, 0.0], dtype=np.float32)
        with (
            patch.object(engine, "_detect_faces", return_value=[(0, 0, 120, 120)]),
            patch.object(
                engine,
                "_face_sample",
                return_value=sample,
            ) as face_sample,
        ):
            engine.cargar_dataset_fotos()
        self.assertEqual(face_sample.call_count, 1)
        self.assertEqual(len(engine.student_embeddings), 1)
        np.testing.assert_array_equal(engine.student_embeddings[1], sample)
        self.assertEqual(len(engine.label_to_student), 1)

        second = self._enroll("TEST-FACE-001", [self.photo] * 5)
        self.assertEqual(second.status_code, 200, second.json)

        conn = database.get_db()
        photos_before_rejection = conn.execute(
            """
            SELECT COUNT(*) FROM fotos_faciales_estudiantes
            WHERE estudiante_id = (
                SELECT id FROM estudiantes WHERE codigo_estudiantil = ?
            )
            """,
            ("TEST-FACE-001",),
        ).fetchone()[0]
        conn.close()
        self.assertEqual(photos_before_rejection, 10)

        overflow = self._enroll("TEST-FACE-001", [self.photo])
        self.assertEqual(overflow.status_code, 409)

        conn = database.get_db()
        photos_after_rejection = conn.execute(
            """
            SELECT COUNT(*) FROM fotos_faciales_estudiantes
            WHERE estudiante_id = (
                SELECT id FROM estudiantes WHERE codigo_estudiantil = ?
            )
            """,
            ("TEST-FACE-001",),
        ).fetchone()[0]
        conn.close()
        self.assertEqual(photos_after_rejection, 10)

    def test_a_single_enrollment_request_accepts_at_most_five_photos(self):
        response = self._enroll("TEST-FACE-004", [self.photo] * 6)

        self.assertEqual(response.status_code, 400)
        self.assertIn("por solicitud", response.get_json()["mensaje"])

    def test_added_photos_do_not_replace_legacy_reference(self):
        conn = database.get_db()
        conn.execute(
            """
            INSERT INTO estudiantes (
                codigo_estudiantil, nombre_completo, nivel_paralelo, foto_path
            ) VALUES (?, ?, ?, ?)
            """,
            (
                "TEST-FACE-002",
                "Estudiante con referencia anterior",
                "Séptimo A - Mañana",
                "legacy-reference.jpg",
            ),
        )
        conn.commit()
        conn.close()

        response = self._enroll("TEST-FACE-002", [self.photo] * 5)
        self.assertEqual(response.status_code, 200, response.json)

        conn = database.get_db()
        legacy_path = conn.execute(
            "SELECT foto_path FROM estudiantes WHERE codigo_estudiantil = ?",
            ("TEST-FACE-002",),
        ).fetchone()["foto_path"]
        added_photos = conn.execute(
            """
            SELECT COUNT(*) FROM fotos_faciales_estudiantes
            WHERE estudiante_id = (
                SELECT id FROM estudiantes WHERE codigo_estudiantil = ?
            )
            """,
            ("TEST-FACE-002",),
        ).fetchone()[0]
        conn.close()
        self.assertEqual(legacy_path, "legacy-reference.jpg")
        self.assertEqual(added_photos, 5)

    def test_yunet_detector_returns_face_landmarks_for_alignment(self):
        engine = FaceEngine.__new__(FaceEngine)
        engine.face_detector = Mock()
        engine._model_lock = threading.Lock()
        detection = np.asarray([[10, 20, 40, 40] + [0.0] * 11], dtype=np.float32)
        engine.face_detector.detect.return_value = (1, detection)

        faces = engine._detect_faces(np.zeros((100, 100, 3), dtype=np.uint8))

        engine.face_detector.setInputSize.assert_called_once_with((100, 100))
        np.testing.assert_array_equal(faces, detection)

    def test_photo_upload_requires_biometric_consent(self):
        response = self._enroll("TEST-FACE-003", [self.photo], consent=False)
        self.assertEqual(response.status_code, 400)
        conn = database.get_db()
        student_count = conn.execute(
            "SELECT COUNT(*) FROM estudiantes WHERE codigo_estudiantil = ?",
            ("TEST-FACE-003",),
        ).fetchone()[0]
        conn.close()
        self.assertEqual(student_count, 0)

    def test_photo_is_rejected_if_saved_jpeg_does_not_have_one_face(self):
        with patch.object(
            server.face_engine,
            "validar_foto_enrolamiento",
            side_effect=[
                (True, ""),
                (False, "La foto debe mostrar exactamente un rostro."),
            ],
        ) as validate_photo:
            response = self._enroll("TEST-FACE-005", [self.photo])

        self.assertEqual(response.status_code, 400)
        self.assertEqual(validate_photo.call_count, 2)
        conn = database.get_db()
        student_count = conn.execute(
            "SELECT COUNT(*) FROM estudiantes WHERE codigo_estudiantil = ?",
            ("TEST-FACE-005",),
        ).fetchone()[0]
        conn.close()
        self.assertEqual(student_count, 0)


if __name__ == "__main__":
    unittest.main()
