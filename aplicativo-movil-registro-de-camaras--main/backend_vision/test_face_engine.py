import unittest
import threading
from unittest.mock import patch

import cv2

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

    def test_stop_live_camera_sets_stop_event(self):
        engine = FaceEngine.__new__(FaceEngine)
        engine._camera_stop_event = threading.Event()

        engine.detener_camara_en_vivo()

        self.assertTrue(engine._camera_stop_event.is_set())


if __name__ == "__main__":
    unittest.main()
