import _pruebas_db  # Debe ir primero: aísla la base de datos real.
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
        _pruebas_db.reiniciar_base_postgres()
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

    def _resumen_en(self, ahora):
        with patch.object(database, "datetime", wraps=datetime) as clock:
            clock.now.return_value = ahora
            return database.obtener_resumen_asistencia(
                materia_id=1,
                fecha=ahora.strftime("%Y-%m-%d"),
            )

    def test_attendance_summary_contains_only_students_enrolled_in_selected_course(self):
        summary = self._resumen_en(datetime(2026, 10, 27, 9, 0, 0))

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

    def test_init_db_keeps_enrolled_demo_students_active(self):
        conn = database.get_db()
        conn.execute(
            """
            INSERT INTO estudiantes
                (codigo_estudiantil, nombre_completo, nivel_paralelo)
            VALUES (?, ?, ?)
            """,
            (
                "UPEC-2026-001",
                "Reina Gordon Jhoel Sebastian",
                "7mo Semestre - Paralelo AM",
            ),
        )
        student_id = conn.execute(
            "SELECT id FROM estudiantes WHERE codigo_estudiantil = ?",
            ("UPEC-2026-001",),
        ).fetchone()["id"]
        database.inscribir_estudiante_en_materia(conn.cursor(), student_id, 1)
        conn.commit()
        conn.close()

        database.init_db()

        conn = database.get_db()
        student = conn.execute(
            "SELECT activo FROM estudiantes WHERE codigo_estudiantil = ?",
            ("UPEC-2026-001",),
        ).fetchone()
        conn.close()
        self.assertEqual(student["activo"], 1)

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
        summary = self._resumen_en(datetime(2026, 10, 27, 11, 0, 0))
        self.assertEqual(summary[0]["estado"], "Parcial")
        self.assertEqual(summary[0]["hora_1_estado"], "Ausente")
        self.assertEqual(summary[0]["hora_2_estado"], "Presente")
        self.assertEqual(
            [period["estado"] for period in summary[0]["periodos"]],
            ["Ausente", "Presente", "Pendiente"],
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

    def test_materias_report_whether_their_schedule_is_currently_active(self):
        conn = database.get_db()
        conn.executemany(
            """
            INSERT INTO materias
                (codigo_materia, nombre_materia, docente_id, docente_nombre,
                 horario)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("ACTIVE-001", "Materia activa", 1, "Docente", "Martes 10:00-11:00"),
                ("INACTIVE-001", "Materia fuera de horario", 1, "Docente",
                 "Martes 11:00-12:00"),
            ],
        )
        conn.commit()
        conn.close()

        with patch.object(database, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 27, 10, 30, 0)
            materias = database.obtener_materias_docente(1)

        estado_por_codigo = {
            materia["codigo_materia"]: materia["horario_activo"]
            for materia in materias
        }
        self.assertTrue(estado_por_codigo["ACTIVE-001"])
        self.assertFalse(estado_por_codigo["INACTIVE-001"])

    def test_facial_scan_in_first_hour_marks_only_the_current_hour(self):
        with patch.object(database, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 27, 10, 5, 0)
            result = database.registrar_asistencia_db(
                self.student_one,
                1,
                metodo="Facial-Telefono",
            )

        self.assertEqual(result["periodos_registrados"], [1])
        summary = self._resumen_en(datetime(2026, 10, 27, 10, 5, 0))
        self.assertEqual(
            [period["estado"] for period in summary[0]["periodos"]],
            ["Presente", "Pendiente", "Pendiente"],
        )

    def test_facial_scan_at_exactly_ten_minutes_is_allowed(self):
        with patch.object(database, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 27, 10, 10, 0)
            result = database.registrar_asistencia_db(
                self.student_one,
                1,
                metodo="Facial-Telefono",
            )

        self.assertEqual(result["periodos_registrados"], [1])
        summary = self._resumen_en(datetime(2026, 10, 27, 10, 10, 0))
        self.assertEqual(
            [period["estado"] for period in summary[0]["periodos"]],
            ["Presente", "Pendiente", "Pendiente"],
        )

    def test_facial_scan_after_first_ten_minutes_keeps_only_current_hour_absent(self):
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

        summary = self._resumen_en(fixed_time)
        self.assertEqual(
            [period["estado"] for period in summary[0]["periodos"]],
            ["Ausente", "Pendiente", "Pendiente"],
        )

    def test_manual_attendance_can_correct_a_hour_after_the_scan_deadline(self):
        fixed_time = datetime(2026, 10, 27, 10, 20, 0)
        with patch.object(database, "datetime", wraps=datetime) as clock:
            clock.now.return_value = fixed_time
            result = database.registrar_asistencia_db(
                self.student_one,
                1,
                estado="Presente",
                metodo="Manual-Docente",
                periodo_indice=1,
            )

        self.assertEqual(result["periodos_registrados"], [1])
        summary = self._resumen_en(fixed_time)
        self.assertEqual(summary[0]["periodos"][0]["estado"], "Presente")
        self.assertEqual(summary[0]["periodos"][1]["estado"], "Pendiente")

    def test_facial_scan_before_hour_start_is_rejected(self):
        with patch.object(database, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 27, 9, 59, 0)
            with self.assertRaisesRegex(ValueError, "hora lectiva"):
                database.registrar_asistencia_db(
                    self.student_one,
                    1,
                    metodo="Facial-Telefono",
                )

        summary = self._resumen_en(datetime(2026, 10, 27, 9, 59, 0))
        self.assertEqual(
            [period["estado"] for period in summary[0]["periodos"]],
            ["Pendiente", "Pendiente", "Pendiente"],
        )

    def test_facial_scan_in_second_hour_preserves_first_hour_absence(self):
        with patch.object(database, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 27, 11, 5, 0)
            result = database.registrar_asistencia_db(
                self.student_one,
                1,
                metodo="Facial-Telefono",
            )

        self.assertEqual(result["periodos_registrados"], [2])
        summary = self._resumen_en(datetime(2026, 10, 27, 11, 5, 0))
        self.assertEqual(
            [period["estado"] for period in summary[0]["periodos"]],
            ["Ausente", "Presente", "Pendiente"],
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

        summary = self._resumen_en(datetime(2026, 10, 27, 10, 7, 0))
        self.assertEqual(
            [period["estado"] for period in summary[0]["periodos"]],
            ["Presente", "Ausente", "Pendiente"],
        )

    def test_summary_marks_only_the_elapsed_hour_absent_after_its_grace_period(self):
        with patch.object(database, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 27, 10, 10, 1)
            summary = database.obtener_resumen_asistencia(1, "2026-10-27")

        self.assertEqual(
            [period["estado"] for period in summary[0]["periodos"]],
            ["Ausente", "Pendiente", "Pendiente"],
        )

    def test_background_absence_task_waits_until_after_inclusive_ten_minute_limit(self):
        updated = database.aplicar_ausencias_programadas(
            datetime(2026, 10, 27, 10, 10, 0)
        )
        self.assertEqual(updated, 0)

        updated = database.aplicar_ausencias_programadas(
            datetime(2026, 10, 27, 10, 10, 1)
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
        self.assertEqual(statuses, ["Ausente"])

    def test_background_absence_task_marks_each_elapsed_hour_only(self):
        updated = database.aplicar_ausencias_programadas(
            datetime(2026, 10, 27, 11, 10, 1)
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
        self.assertEqual(statuses, ["Ausente", "Ausente"])

    def test_background_absence_task_backfills_all_elapsed_hours_after_class_ends(self):
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
        self.assertEqual(updated, 1)
        self.assertEqual(count, 3)

    def test_manual_attendance_rejects_invalid_status(self):
        with self.assertRaisesRegex(ValueError, "estado de asistencia válido"):
            database.registrar_asistencia_db(
                self.student_one,
                1,
                estado="No válido",
            )

    def test_migration_preserves_enrolled_demo_students_and_history(self):
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
        demo_enrollment = conn.execute(
            """
            SELECT COUNT(*) FROM materia_estudiantes
            WHERE materia_id = 1 AND estudiante_id = ?
            """,
            (demo_student,),
        ).fetchone()[0]
        attendance_count = conn.execute(
            "SELECT COUNT(*) FROM asistencias WHERE materia_id = 1"
        ).fetchone()[0]
        conn.close()

        self.assertEqual(demo_active, 1)
        self.assertEqual(enrollment, 1)
        self.assertEqual(demo_enrollment, 1)
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




class DemoStudentSeedTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path_patch = patch.object(
            database, "DB_PATH", os.path.join(self.temp_dir.name, "seed.db")
        )
        self.db_path_patch.start()
        self.addCleanup(self.db_path_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)
        _pruebas_db.reiniciar_base_postgres()

    def test_server_start_does_not_force_demo_students(self):
        database.init_db()
        conn = database.get_db()
        try:
            total = conn.execute("SELECT COUNT(*) FROM estudiantes").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(total, 0)

    def test_seed_script_is_idempotent_and_only_links_existing_photos(self):
        import sembrar_estudiantes_demo

        dataset_dir = os.path.join(self.temp_dir.name, "faces")
        os.makedirs(dataset_dir)
        codigo, _, _, _, foto = database.ESTUDIANTES_DEMOSTRACION[0]
        open(os.path.join(dataset_dir, foto), "wb").close()
        with patch.object(sembrar_estudiantes_demo, "DATASET_DIR", dataset_dir), \
                patch("builtins.print"):
            sembrar_estudiantes_demo.sembrar([1, 2])
            sembrar_estudiantes_demo.sembrar([1, 2])

        conn = database.get_db()
        try:
            estudiantes = conn.execute(
                "SELECT COUNT(*) FROM estudiantes WHERE activo = 1"
            ).fetchone()[0]
            inscripciones = conn.execute(
                "SELECT COUNT(*) FROM materia_estudiantes"
            ).fetchone()[0]
            fotos = conn.execute(
                "SELECT f.foto_path FROM fotos_faciales_estudiantes f "
                "JOIN estudiantes e ON e.id = f.estudiante_id"
            ).fetchall()
        finally:
            conn.close()
        total = len(database.ESTUDIANTES_DEMOSTRACION)
        self.assertEqual(estudiantes, total)
        self.assertEqual(inscripciones, total * 2)
        self.assertEqual([row[0] for row in fotos], [foto])

if __name__ == "__main__":
    unittest.main()
