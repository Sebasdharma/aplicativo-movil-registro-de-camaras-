import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

import database


class MateriaEnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "attendance.db")
        self.db_path_patch = patch.object(database, "DB_PATH", self.db_path)
        self.db_path_patch.start()
        self.addCleanup(self.db_path_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)
        database.init_db()
        self.conn = database.get_db()
        self.conn.executemany(
            """
            INSERT INTO estudiantes
                (codigo_estudiantil, nombre_completo, nivel_paralelo)
            VALUES (?, ?, ?)
            """,
            [
                ("REAL-001", "Estudiante Uno", "Nivel 1"),
                ("REAL-002", "Estudiante Dos", "Nivel 2"),
            ],
        )
        self.conn.commit()
        self.student_one = self.conn.execute(
            "SELECT id FROM estudiantes WHERE codigo_estudiantil = 'REAL-001'"
        ).fetchone()["id"]
        self.student_two = self.conn.execute(
            "SELECT id FROM estudiantes WHERE codigo_estudiantil = 'REAL-002'"
        ).fetchone()["id"]
        database.inscribir_estudiante_en_materia(
            self.conn.cursor(), self.student_one, 1
        )
        database.inscribir_estudiante_en_materia(
            self.conn.cursor(), self.student_two, 2
        )
        self.conn.commit()
        self.conn.close()

    def test_attendance_summary_contains_only_students_enrolled_in_selected_course(self):
        summary = database.obtener_resumen_asistencia(materia_id=1)

        self.assertEqual([row["codigo_estudiantil"] for row in summary], ["REAL-001"])
        self.assertEqual(summary[0]["hora_1_estado"], "Pendiente")

        conn = database.get_db()
        attendance_count = conn.execute(
            "SELECT COUNT(*) FROM asistencias"
        ).fetchone()[0]
        conn.close()
        self.assertEqual(attendance_count, 0)

    def test_init_db_repairs_mojibake_student_schedule(self):
        conn = database.get_db()
        conn.execute(
            """
            INSERT INTO estudiantes
                (codigo_estudiantil, nombre_completo, nivel_paralelo)
            VALUES (?, ?, ?)
            """,
            ("BROKEN-001", "Estudiante con texto dañado", "S?ptimo A - Ma?ana"),
        )
        conn.commit()
        conn.close()

        database.init_db()

        conn = database.get_db()
        level = conn.execute(
            "SELECT nivel_paralelo FROM estudiantes WHERE codigo_estudiantil = ?",
            ("BROKEN-001",),
        ).fetchone()["nivel_paralelo"]
        conn.close()
        self.assertEqual(level, "Séptimo A - Mañana")

    def test_manual_attendance_rejects_student_not_enrolled_in_course(self):
        with self.assertRaisesRegex(ValueError, "no está inscrito"):
            database.registrar_asistencia_db(self.student_two, 1)

    def test_manual_attendance_summary_reports_present_in_the_second_hour(self):
        with patch.object(database, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 27, 11, 0, 0)
            result = database.registrar_asistencia_db(
                self.student_one,
                1,
                estado="Presente",
                metodo="Manual-Docente",
                periodo_indice=2,
            )

        self.assertEqual(result["status"], "ok")
        summary = database.obtener_resumen_asistencia(
            materia_id=1,
            fecha="2026-10-27",
        )
        self.assertEqual(summary[0]["estado"], "Parcial")
        self.assertEqual(summary[0]["hora_1_estado"], "Ausente")
        self.assertEqual(summary[0]["hora_2_estado"], "Presente")
        self.assertEqual(
            [period["estado"] for period in summary[0]["periodos"]],
            ["Ausente", "Presente", "Ausente"],
        )

    def test_schedule_splits_class_hours_and_excludes_tutorials(self):
        periods = database.obtener_periodos_lectivos(
            "Martes 10:00-13:00 clase\n"
            "Miércoles 09:00-10:00 tutoría\n"
            "Miércoles 11:00-13:00 clase",
            "2026-10-27",
        )

        self.assertEqual(
            [(period["inicio"], period["fin"]) for period in periods],
            [("10:00", "11:00"), ("11:00", "12:00"), ("12:00", "13:00")],
        )

    def test_facial_scan_in_first_hour_marks_all_hours_of_that_class_block(self):
        with patch.object(database, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 27, 10, 5, 0)
            result = database.registrar_asistencia_db(
                self.student_one,
                1,
                metodo="Facial-Telefono",
            )

        self.assertEqual(result["periodos_registrados"], [1, 2, 3])
        summary = database.obtener_resumen_asistencia(1, "2026-10-27")
        self.assertEqual(
            [period["estado"] for period in summary[0]["periodos"]],
            ["Presente", "Presente", "Presente"],
        )

    def test_facial_scan_after_first_ten_minutes_keeps_block_absent(self):
        fixed_time = datetime(2026, 10, 27, 10, 11, 0)
        database.aplicar_ausencias_programadas(fixed_time)

        with patch.object(database, "datetime", wraps=datetime) as clock:
            clock.now.return_value = fixed_time
            with self.assertRaisesRegex(ValueError, "primeros 10 minutos"):
                database.registrar_asistencia_db(
                    self.student_one,
                    1,
                    metodo="Facial-Telefono",
                )

        summary = database.obtener_resumen_asistencia(1, "2026-10-27")
        self.assertEqual(
            [period["estado"] for period in summary[0]["periodos"]],
            ["Ausente", "Ausente", "Ausente"],
        )

    def test_facial_scan_in_second_hour_preserves_first_hour_absence(self):
        with patch.object(database, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 27, 11, 5, 0)
            result = database.registrar_asistencia_db(
                self.student_one,
                1,
                metodo="Facial-Telefono",
            )

        self.assertEqual(result["periodos_registrados"], [2, 3])
        summary = database.obtener_resumen_asistencia(1, "2026-10-27")
        self.assertEqual(
            [period["estado"] for period in summary[0]["periodos"]],
            ["Ausente", "Presente", "Presente"],
        )

    def test_manual_period_change_is_not_overwritten_by_later_facial_frames(self):
        with patch.object(database, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 27, 10, 5, 0)
            database.registrar_asistencia_db(
                self.student_one,
                1,
                metodo="Facial-Telefono",
            )
            clock.now.return_value = datetime(2026, 10, 27, 10, 6, 0)
            database.registrar_asistencia_db(
                self.student_one,
                1,
                estado="Ausente",
                metodo="Manual-Docente",
                periodo_indice=2,
            )
            clock.now.return_value = datetime(2026, 10, 27, 10, 7, 0)
            database.registrar_asistencia_db(
                self.student_one,
                1,
                metodo="Facial-Telefono",
            )

        summary = database.obtener_resumen_asistencia(1, "2026-10-27")
        self.assertEqual(
            [period["estado"] for period in summary[0]["periodos"]],
            ["Presente", "Ausente", "Presente"],
        )

    def test_summary_marks_every_hour_absent_ten_minutes_after_class_start(self):
        with patch.object(database, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 27, 10, 10, 0)
            summary = database.obtener_resumen_asistencia(1, "2026-10-27")

        self.assertEqual(
            [period["estado"] for period in summary[0]["periodos"]],
            ["Ausente", "Ausente", "Ausente"],
        )

    def test_background_absence_task_marks_all_periods_after_ten_minutes(self):
        updated = database.aplicar_ausencias_programadas(
            datetime(2026, 10, 27, 10, 10, 0)
        )

        conn = database.get_db()
        statuses = [
            row["estado"]
            for row in conn.execute(
                """
                SELECT estado FROM asistencia_periodos
                WHERE estudiante_id = ? AND materia_id = 1
                  AND fecha = '2026-10-27'
                ORDER BY periodo_indice
                """,
                (self.student_one,),
            )
        ]
        conn.close()
        self.assertEqual(updated, 1)
        self.assertEqual(statuses, ["Ausente", "Ausente", "Ausente"])

    def test_background_absence_task_does_not_backfill_after_class_ends(self):
        updated = database.aplicar_ausencias_programadas(
            datetime(2026, 10, 27, 13, 0, 0)
        )

        conn = database.get_db()
        count = conn.execute(
            """
            SELECT COUNT(*) FROM asistencia_periodos
            WHERE estudiante_id = ? AND materia_id = 1
              AND fecha = '2026-10-27'
            """,
            (self.student_one,),
        ).fetchone()[0]
        conn.close()
        self.assertEqual(updated, 0)
        self.assertEqual(count, 0)

    def test_manual_attendance_rejects_invalid_status(self):
        with self.assertRaisesRegex(ValueError, "estado de asistencia válido"):
            database.registrar_asistencia_db(
                self.student_one,
                1,
                estado="No válido",
            )

    def test_migration_hides_known_demo_students_and_preserves_history(self):
        conn = database.get_db()
        conn.execute(
            """
            INSERT INTO estudiantes
                (codigo_estudiantil, nombre_completo, nivel_paralelo)
            VALUES ('UPEC-2026-001', 'Reina Gordon Jhoel Sebastian', 'Demo')
            """
        )
        demo_student = conn.execute(
            "SELECT id FROM estudiantes WHERE codigo_estudiantil = 'UPEC-2026-001'"
        ).fetchone()["id"]
        conn.execute(
            """
            INSERT INTO asistencias
                (estudiante_id, materia_id, fecha, estado, hora)
            VALUES (?, 1, ?, 'Presente', ?)
            """,
            (self.student_one, datetime.now().strftime("%Y-%m-%d"), "07:05:00"),
        )
        conn.execute(
            """
            INSERT INTO asistencias
                (estudiante_id, materia_id, fecha, estado, hora)
            VALUES (?, 1, ?, 'Presente', ?)
            """,
            (demo_student, datetime.now().strftime("%Y-%m-%d"), "07:06:00"),
        )
        conn.execute("DROP TABLE materia_estudiantes")
        conn.commit()
        conn.close()

        database.init_db()

        conn = database.get_db()
        demo_active = conn.execute(
            "SELECT activo FROM estudiantes WHERE id = ?", (demo_student,)
        ).fetchone()["activo"]
        enrollment = conn.execute(
            """
            SELECT COUNT(*) FROM materia_estudiantes
            WHERE materia_id = 1 AND estudiante_id = ?
            """,
            (self.student_one,),
        ).fetchone()[0]
        attendance_count = conn.execute(
            "SELECT COUNT(*) FROM asistencias WHERE materia_id = 1"
        ).fetchone()[0]
        conn.close()

        self.assertEqual(demo_active, 0)
        self.assertEqual(enrollment, 1)
        self.assertEqual(attendance_count, 2)
        self.assertEqual(database.obtener_dispositivos_iot(), [])

    def test_migration_keeps_photo_enrolled_demo_name_active(self):
        conn = database.get_db()
        conn.execute(
            """
            INSERT INTO estudiantes (
                codigo_estudiantil, nombre_completo, nivel_paralelo, foto_path
            ) VALUES (?, ?, ?, ?)
            """,
            (
                "UPEC-2026-001",
                "Reina Gordon Jhoel Sebastian",
                "Séptimo A - Mañana",
                "UPEC-2026-001-reference.jpg",
            ),
        )
        conn.commit()
        conn.close()

        database.init_db()

        conn = database.get_db()
        active = conn.execute(
            """
            SELECT activo FROM estudiantes
            WHERE codigo_estudiantil = 'UPEC-2026-001'
            """
        ).fetchone()["activo"]
        conn.close()

        self.assertEqual(active, 1)

    def test_default_teacher_identity_is_administrator(self):
        conn = database.get_db()
        teacher_names = [
            row["nombre_completo"]
            for row in conn.execute("SELECT nombre_completo FROM docentes")
        ]
        schedule_courses = [
            dict(row)
            for row in conn.execute(
                """
                SELECT codigo_materia, nombre_materia, docente_id,
                       docente_nombre, horario, aula, nivel_paralelo, activo
                FROM materias
                WHERE activo = 1
                ORDER BY codigo_materia
                """
            )
        ]
        conn.close()

        self.assertEqual(teacher_names, ["Administrador", "Jordy Lema"])
        self.assertEqual(len(schedule_courses), 5)
        self.assertEqual(
            [course["nombre_materia"] for course in schedule_courses],
            [
                "Aplicaciones Móviles",
                "Visión por Computador",
                "Seguridad Informática",
                "Normativas de Ingeniería de Software",
                "Redes de Computadoras y Seguridades",
            ],
        )
        self.assertEqual(
            schedule_courses[0]["horario"],
            "Martes 10:00-13:00 clase\n"
            "Miércoles 10:00-11:00 tutoría\n"
            "Jueves 10:00-13:00 clase",
        )
        self.assertEqual(
            {course["nivel_paralelo"] for course in schedule_courses},
            {"Séptimo A - Mañana"},
        )
        self.assertEqual(
            {course["aula"] for course in schedule_courses},
            {"No indicado"},
        )
        self.assertEqual(
            {course["docente_id"] for course in schedule_courses},
            {2},
        )
        self.assertEqual(
            [course["docente_nombre"] for course in schedule_courses],
            [
                "Lascano Samuel",
                "Jimenez Stalin",
                "Hidalgo Jairo",
                "Lascano Samuel",
                "Del Hierro Milton",
            ],
        )

    def test_administrator_can_list_all_active_courses(self):
        admin_courses = database.obtener_materias_docente(docente_id=1)
        teacher_courses = database.obtener_materias_docente(docente_id=2)

        self.assertEqual(len(admin_courses), 5)
        self.assertEqual(
            [course["id"] for course in admin_courses],
            [course["id"] for course in teacher_courses],
        )

    def test_legacy_iot_demo_is_archived_without_deleting_its_attendance(self):
        conn = database.get_db()
        conn.execute(
            """
            UPDATE materias
            SET nombre_materia = 'Redes e Internet de las Cosas (IoT)'
            WHERE codigo_materia = 'COMP-703'
            """
        )
        conn.execute(
            """
            INSERT INTO asistencias
                (estudiante_id, materia_id, fecha, estado, hora)
            VALUES (?, 3, ?, 'Presente', ?)
            """,
            (self.student_one, datetime.now().strftime("%Y-%m-%d"), "08:05:00"),
        )
        conn.commit()
        conn.close()

        database.init_db()

        conn = database.get_db()
        old_course = conn.execute(
            "SELECT activo FROM materias WHERE codigo_materia = 'COMP-703'"
        ).fetchone()
        old_attendance = conn.execute(
            "SELECT COUNT(*) FROM asistencias WHERE materia_id = 3"
        ).fetchone()[0]
        replacement = conn.execute(
            """
            SELECT nombre_materia FROM materias
            WHERE codigo_materia = 'COMP-706' AND activo = 1
            """
        ).fetchone()
        conn.close()

        self.assertEqual(old_course["activo"], 0)
        self.assertEqual(old_attendance, 1)
        self.assertEqual(replacement["nombre_materia"], "Seguridad Informática")


if __name__ == "__main__":
    unittest.main()
