import os
import sqlite3
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

import carchito_voice


class CarchitoVoiceAssistantTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "carchito-test.db")
        self._create_database()
        self.db_patch = patch.object(carchito_voice, "get_db", self._get_db)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)
        self.assistant = carchito_voice.CarchitoVoiceAssistant()

    def _get_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_database(self):
        conn = self._get_db()
        conn.executescript(
            """
            CREATE TABLE materias (id INTEGER PRIMARY KEY, nombre_materia TEXT);
            CREATE TABLE estudiantes (
                id INTEGER PRIMARY KEY,
                activo INTEGER NOT NULL
            );
            CREATE TABLE materia_estudiantes (
                materia_id INTEGER,
                estudiante_id INTEGER,
                PRIMARY KEY (materia_id, estudiante_id)
            );
            CREATE TABLE asistencias (
                estudiante_id INTEGER,
                materia_id INTEGER,
                fecha TEXT,
                hora_1_estado TEXT,
                hora_2_estado TEXT,
                metodo_registro TEXT
            );
            CREATE TABLE asistencia_periodos (
                estudiante_id INTEGER,
                materia_id INTEGER,
                fecha TEXT,
                periodo_indice INTEGER,
                bloque_indice INTEGER,
                inicio TEXT,
                fin TEXT,
                estado TEXT,
                hora TEXT,
                metodo_registro TEXT
            );
            INSERT INTO materias VALUES (1, 'Aplicaciones Móviles');
            INSERT INTO materias VALUES (2, 'Visión por Computador');
            INSERT INTO estudiantes VALUES (1, 1);
            INSERT INTO estudiantes VALUES (2, 1);
            INSERT INTO estudiantes VALUES (3, 1);
            INSERT INTO materia_estudiantes VALUES (1, 1);
            INSERT INTO materia_estudiantes VALUES (1, 2);
            INSERT INTO materia_estudiantes VALUES (1, 3);
            """
        )
        conn.commit()
        conn.close()

    def test_requires_exact_wake_phrase(self):
        result = self.assistant.procesar_comando("Carchito, toma lista")

        self.assertEqual(result["accion"], "desconocido")
        self.assertIn("Hola Carchito", result["mensaje"])

    def test_help_returns_supported_commands(self):
        result = self.assistant.procesar_comando("Hola Carchito, ayuda")

        self.assertEqual(result["accion"], "ayuda")
        self.assertIn("toma lista", result["mensaje"])
        self.assertIn("reporte", result["mensaje"])

    def test_scan_without_face_references_is_explicit(self):
        result = self.assistant.procesar_comando(
            "Hola Carchito, toma lista de Aplicaciones Móviles",
            muestras_faciales=0,
        )

        self.assertEqual(result["accion"], "iniciar_escaneo")
        self.assertEqual(result["muestras_faciales"], 0)
        self.assertIn("no identificaré estudiantes", result["mensaje"])
        self.assertIn("ni registraré asistencias", result["mensaje"])

    def test_scan_rejects_a_different_selected_subject(self):
        result = self.assistant.procesar_comando(
            "Hola Carchito, toma lista de Visión por Computador",
            materia_id=1,
        )

        self.assertEqual(result["accion"], "materia_no_coincide")
        self.assertIn("Selecciona esa materia", result["mensaje"])

    def test_report_counts_only_attendance_registered_for_the_selected_course(self):
        conn = self._get_db()
        fecha = datetime.now().strftime("%Y-%m-%d")
        conn.executemany(
            """
            INSERT INTO asistencias
                (estudiante_id, materia_id, fecha, hora_1_estado, hora_2_estado, metodo_registro)
            VALUES (?, 1, ?, ?, ?, ?)
            """,
            [
                (1, fecha, "Presente", "Pendiente", "Manual-Docente"),
                (2, fecha, "Ausente", "Presente", "Facial-Telefono"),
            ],
        )
        conn.commit()
        conn.close()

        result = self.assistant.procesar_comando(
            "Hola Carchito, dame el reporte de asistencia"
        )

        self.assertEqual(result["accion"], "consultar_reporte")
        self.assertEqual(result["estudiantes_con_registro"], 2)
        self.assertEqual(
            result["reporte"]["hora_1"],
            {"presentes": 1, "ausentes": 1},
        )
        self.assertEqual(
            result["reporte"]["hora_2"],
            {"presentes": 1, "ausentes": 0},
        )
        self.assertIn("falta asociar la lista", result["mensaje"])

    def test_report_ignores_automatic_absence_rules(self):
        conn = self._get_db()
        fecha = datetime.now().strftime("%Y-%m-%d")
        conn.execute(
            """
            INSERT INTO asistencias
                (estudiante_id, materia_id, fecha, hora_1_estado, hora_2_estado, metodo_registro)
            VALUES (1, 1, ?, 'Ausente', 'Pendiente', 'Regla-10min')
            """,
            (fecha,),
        )
        conn.commit()
        conn.close()

        result = self.assistant.procesar_comando(
            "Hola Carchito, reporte de asistencia"
        )

        self.assertEqual(result["estudiantes_con_registro"], 0)
        self.assertIn("no hay registros de asistencia", result["mensaje"])

    def test_report_includes_all_scheduled_hours_when_attendance_is_recorded(self):
        conn = self._get_db()
        fecha = datetime.now().strftime("%Y-%m-%d")
        conn.executemany(
            """
            INSERT INTO asistencia_periodos (
                estudiante_id, materia_id, fecha, periodo_indice,
                bloque_indice, inicio, fin, estado, hora, metodo_registro
            ) VALUES (?, 1, ?, ?, 1, '10:00', '11:00', ?, ?, ?)
            """,
            [
                (1, fecha, 1, "Presente", "10:05:00", "Facial-Telefono"),
                (1, fecha, 2, "Ausente", "--:--:--", "Regla-10min"),
                (1, fecha, 3, "Ausente", "--:--:--", "Regla-10min"),
                (2, fecha, 1, "Ausente", "--:--:--", "Manual-Docente"),
                (2, fecha, 2, "Presente", "11:02:00", "Manual-Docente"),
                (2, fecha, 3, "Presente", "11:02:00", "Facial-Telefono"),
            ],
        )
        conn.commit()
        conn.close()

        result = self.assistant.procesar_comando(
            "Hola Carchito, dame el reporte de asistencia"
        )

        self.assertEqual(result["estudiantes_con_registro"], 2)
        self.assertEqual(
            result["reporte"],
            {
                "hora_1": {"presentes": 1, "ausentes": 1},
                "hora_2": {"presentes": 1, "ausentes": 1},
                "hora_3": {"presentes": 1, "ausentes": 1},
            },
        )

    def test_report_without_attendance_does_not_invent_absences_or_pending_students(self):
        result = self.assistant.procesar_comando(
            "Hola Carchito, dame el reporte de asistencia"
        )

        self.assertEqual(result["estudiantes_con_registro"], 0)
        self.assertEqual(
            result["reporte"],
            {
                "hora_1": {"presentes": 0, "ausentes": 0},
                "hora_2": {"presentes": 0, "ausentes": 0},
            },
        )
        self.assertIn("no hay registros de asistencia", result["mensaje"])
        self.assertIn("no puedo calcular estudiantes pendientes", result["mensaje"])


if __name__ == "__main__":
    unittest.main()
