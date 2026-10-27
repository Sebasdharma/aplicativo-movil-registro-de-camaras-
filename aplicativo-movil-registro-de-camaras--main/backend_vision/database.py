import sqlite3
import os
import re
import unicodedata
from datetime import date, datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "buhopass.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _ensure_columns(cursor, table, columns):
    existing = {row["name"] for row in cursor.execute(f"PRAGMA table_info({table})")}
    for name, definition in columns.items():
        if name not in existing:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Tabla de Docentes Institucionales (UPEC)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS docentes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_institucional TEXT UNIQUE NOT NULL,
        nombre_completo TEXT NOT NULL,
        cedula TEXT,
        facultad TEXT NOT NULL,
        carrera TEXT NOT NULL,
        auth_provider TEXT DEFAULT 'microsoft'
    )
    """)

    # Tabla de Materias
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS materias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_materia TEXT UNIQUE NOT NULL,
        nombre_materia TEXT NOT NULL,
        docente_id INTEGER,
        docente_nombre TEXT NOT NULL,
        horario TEXT,
        aula TEXT DEFAULT 'Lab. Computación 3',
        periodo TEXT DEFAULT '2026-B',
        nivel_paralelo TEXT DEFAULT 'Séptimo A - Mañana',
        activo INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (docente_id) REFERENCES docentes (id)
    )
    """)

    # Tabla de Estudiantes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estudiantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_estudiantil TEXT UNIQUE NOT NULL,
        nombre_completo TEXT NOT NULL,
        nivel_paralelo TEXT NOT NULL,
        email TEXT,
        foto_path TEXT,
        activo INTEGER DEFAULT 1
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS materia_estudiantes (
        materia_id INTEGER NOT NULL,
        estudiante_id INTEGER NOT NULL,
        fecha_inscripcion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (materia_id, estudiante_id),
        FOREIGN KEY (materia_id) REFERENCES materias (id),
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fotos_faciales_estudiantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER NOT NULL,
        foto_path TEXT NOT NULL UNIQUE,
        fecha_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes (id)
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_fotos_faciales_estudiante
    ON fotos_faciales_estudiantes (estudiante_id)
    """)

    # Tabla de Dispositivos IoT / Cámaras de Aula
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dispositivos_iot (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        tipo TEXT NOT NULL, -- 'ESP32-CAM', 'Webcam-USB', 'RTSP-IP'
        ip_address TEXT,
        aula TEXT NOT NULL,
        estado TEXT DEFAULT 'Conectado', -- 'Conectado', 'Desconectado', 'Transmitiendo'
        ultima_actividad TEXT
    )
    """)
    
    # Tabla de Registros de Asistencia por Horas (Hora 1 y Hora 2)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS asistencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER NOT NULL,
        materia_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        estado TEXT NOT NULL, -- Estado general ('Presente', 'Ausente', 'Atrasado', 'Hora 2 Presente')
        hora TEXT NOT NULL,
        metodo_registro TEXT DEFAULT 'Facial-Carchito',
        dispositivo_id INTEGER,
        hora_1_estado TEXT DEFAULT 'Pendiente', -- 'Presente', 'Ausente', 'Atrasado'
        hora_1_hora TEXT DEFAULT '--:--:--',
        hora_2_estado TEXT DEFAULT 'Pendiente', -- 'Presente', 'Ausente'
        hora_2_hora TEXT DEFAULT '--:--:--',
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes (id),
        FOREIGN KEY (materia_id) REFERENCES materias (id),
        FOREIGN KEY (dispositivo_id) REFERENCES dispositivos_iot (id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS asistencia_periodos (
        estudiante_id INTEGER NOT NULL,
        materia_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        periodo_indice INTEGER NOT NULL,
        bloque_indice INTEGER NOT NULL,
        inicio TEXT NOT NULL,
        fin TEXT NOT NULL,
        estado TEXT NOT NULL,
        hora TEXT NOT NULL DEFAULT '--:--:--',
        metodo_registro TEXT NOT NULL,
        PRIMARY KEY (estudiante_id, materia_id, fecha, periodo_indice),
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes (id),
        FOREIGN KEY (materia_id) REFERENCES materias (id)
    )
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_asistencia_periodos_materia_fecha
    ON asistencia_periodos (materia_id, fecha, periodo_indice)
    """)

    _ensure_columns(cursor, "materias", {
        "docente_id": "INTEGER",
        "docente_nombre": "TEXT",
        "aula": "TEXT DEFAULT 'Lab. Computación 3'",
        "periodo": "TEXT DEFAULT '2026-B'",
        "nivel_paralelo": "TEXT DEFAULT 'Séptimo A - Mañana'",
        "activo": "INTEGER NOT NULL DEFAULT 1",
    })
    _ensure_columns(cursor, "asistencias", {
        "hora_1_estado": "TEXT DEFAULT 'Pendiente'",
        "hora_1_hora": "TEXT DEFAULT '--:--:--'",
        "hora_2_estado": "TEXT DEFAULT 'Pendiente'",
        "hora_2_hora": "TEXT DEFAULT '--:--:--'",
    })
    cursor.execute(
        """
        UPDATE estudiantes
        SET nivel_paralelo = ?
        WHERE nivel_paralelo = ?
        """,
        ("Séptimo A - Mañana", "S?ptimo A - Ma?ana"),
    )
    conn.commit()

    
    # Insertar docente institucional semilla si no existe
    cursor.execute("SELECT COUNT(*) FROM docentes")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO docentes (email_institucional, nombre_completo, cedula, facultad, carrera)
        VALUES (?, ?, ?, ?, ?)
        """, (
            "admin@upec.edu.ec",
            "Administrador",
            None,
            "Facultad de Industrias Agropecuarias y Ciencias Ambientales (FIACA)",
            "Carrera de Computación"
        ))

    cursor.execute("""
    UPDATE docentes
    SET email_institucional = ?, nombre_completo = ?, cedula = NULL
    WHERE email_institucional = ?
    """, (
        "admin@upec.edu.ec",
        "Administrador",
        "samuel.lascano@upec.edu.ec",
    ))

    cursor.execute("""
    INSERT OR IGNORE INTO docentes (email_institucional, nombre_completo, cedula, facultad, carrera)
    VALUES (?, ?, ?, ?, ?)
    """, (
        "jordy.lema@upec.edu.ec",
        "Jordy Lema",
        "0401234567",
        "Facultad de Industrias Agropecuarias y Ciencias Ambientales (FIACA)",
        "Carrera de Computación",
    ))

    materia_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(materias)")
    }
    if "docente" in materia_columns:
        cursor.execute("""
        UPDATE materias
        SET docente_nombre = docente
        WHERE docente_nombre IS NULL OR docente_nombre = ''
        """)
        cursor.execute("""
        UPDATE materias
        SET docente_id = (
            SELECT id FROM docentes WHERE nombre_completo = materias.docente
            ORDER BY id LIMIT 1
        )
        WHERE docente_id IS NULL
        """)
    cursor.execute("""
    UPDATE materias
    SET docente_id = (SELECT MIN(id) FROM docentes)
    WHERE docente_id IS NULL
    """)
    cursor.execute("""
    UPDATE materias
    SET docente_nombre = (
        SELECT nombre_completo FROM docentes WHERE id = materias.docente_id
    )
    WHERE docente_nombre IS NULL OR docente_nombre = ''
    """)
    cursor.execute("""
    UPDATE materias
    SET docente_nombre = 'Administrador'
    WHERE docente_id = (SELECT MIN(id) FROM docentes)
    """)
    if "docente" in materia_columns:
        cursor.execute("""
        UPDATE materias
        SET docente = 'Administrador'
        WHERE docente_id = (SELECT MIN(id) FROM docentes)
        """)
    cursor.execute("""
    UPDATE materias SET aula = 'Lab. Computación 3'
    WHERE aula IS NULL OR aula = ''
    """)
    cursor.execute("""
    UPDATE materias SET periodo = '2026-B'
    WHERE periodo IS NULL OR periodo = ''
    """)
    cursor.execute("""
    UPDATE materias SET nombre_materia = ?
    WHERE codigo_materia = ? AND instr(nombre_materia, char(65533)) > 0
    """, ("Aplicaciones Móviles", "COMP-701"))
    
    schedule_owner = cursor.execute(
        """
        SELECT id FROM docentes
        WHERE LOWER(email_institucional) = LOWER('jordy.lema@upec.edu.ec')
        """
    ).fetchone()
    schedule_owner_id = (
        schedule_owner["id"]
        if schedule_owner
        else cursor.execute("SELECT MIN(id) FROM docentes").fetchone()[0]
    )
    materias_semilla = [
        (
            "COMP-701",
            "Aplicaciones Móviles",
            "Lascano Samuel",
            "Martes 10:00-13:00 clase\n"
            "Miércoles 10:00-11:00 tutoría\n"
            "Jueves 10:00-13:00 clase",
        ),
        (
            "COMP-702",
            "Visión por Computador",
            "Jimenez Stalin",
            "Miércoles 09:00-10:00 tutoría\n"
            "Viernes 11:00-13:00 clase",
        ),
        (
            "COMP-703",
            "Seguridad Informática",
            "Hidalgo Jairo",
            "Jueves 09:00-10:00 tutoría\n"
            "Viernes 08:00-11:00 clase",
        ),
        (
            "COMP-704",
            "Normativas de Ingeniería de Software",
            "Lascano Samuel",
            "Lunes 10:00-12:00 clase\n"
            "Lunes 12:00-13:00 tutoría\n"
            "Miércoles 11:00-13:00 clase",
        ),
        (
            "COMP-705",
            "Redes de Computadoras y Seguridades",
            "Del Hierro Milton",
            "Martes 07:00-09:00 clase\n"
            "Martes 09:00-10:00 tutoría\n"
            "Jueves 07:00-09:00 clase",
        ),
    ]
    legacy_iot = cursor.execute(
        """
        SELECT id FROM materias
        WHERE codigo_materia = 'COMP-703'
          AND nombre_materia = 'Redes e Internet de las Cosas (IoT)'
        """
    ).fetchone()
    if legacy_iot:
        cursor.execute(
            "UPDATE materias SET activo = 0 WHERE id = ?",
            (legacy_iot["id"],),
        )
        materias_semilla[2] = (
            "COMP-706",
            "Seguridad Informática",
            "Hidalgo Jairo",
            "Jueves 09:00-10:00 tutoría\nViernes 08:00-11:00 clase",
        )

    materias_demo_anteriores = {
        "COMP-701": {"Aplicaciones Móviles"},
        "COMP-702": {"Visión por Computador"},
        "COMP-703": {
            "Seguridad Informática",
            "Redes e Internet de las Cosas (IoT)",
        },
    }
    for codigo, nombre, docente_nombre, horario in materias_semilla:
        existing = cursor.execute(
            """
            SELECT id, nombre_materia FROM materias
            WHERE codigo_materia = ?
            """,
            (codigo,),
        ).fetchone()
        if existing is None:
            if "docente" in materia_columns:
                cursor.execute(
                    """
                    INSERT INTO materias (
                        codigo_materia, nombre_materia, docente_id, docente_nombre,
                        docente, horario, aula, periodo, nivel_paralelo, activo
                    ) VALUES (?, ?, ?, ?, ?, ?, 'No indicado', '2026-B', 'Séptimo A - Mañana', 1)
                    """,
                    (
                        codigo,
                        nombre,
                        schedule_owner_id,
                        docente_nombre,
                        docente_nombre,
                        horario,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO materias (
                        codigo_materia, nombre_materia, docente_id, docente_nombre,
                        horario, aula, periodo, nivel_paralelo, activo
                    ) VALUES (?, ?, ?, ?, ?, 'No indicado', '2026-B', 'Séptimo A - Mañana', 1)
                    """,
                    (
                        codigo,
                        nombre,
                        schedule_owner_id,
                        docente_nombre,
                        horario,
                    ),
                )
            continue

        nombres_actualizables = materias_demo_anteriores.get(codigo, {nombre})
        if existing["nombre_materia"] not in nombres_actualizables:
            continue

        if "docente" in materia_columns:
            cursor.execute(
                """
                UPDATE materias
                SET nombre_materia = ?, docente_id = ?, docente_nombre = ?,
                    docente = ?, horario = ?, aula = 'No indicado',
                    periodo = '2026-B',
                    nivel_paralelo = 'Séptimo A - Mañana', activo = 1
                WHERE id = ?
                """,
                (
                    nombre,
                    schedule_owner_id,
                    docente_nombre,
                    docente_nombre,
                    horario,
                    existing["id"],
                ),
            )
        else:
            cursor.execute(
                """
                UPDATE materias
                SET nombre_materia = ?, docente_id = ?, docente_nombre = ?,
                    horario = ?, aula = 'No indicado', periodo = '2026-B',
                    nivel_paralelo = 'Séptimo A - Mañana', activo = 1
                WHERE id = ?
                """,
                (
                    nombre,
                    schedule_owner_id,
                    docente_nombre,
                    horario,
                    existing["id"],
                ),
            )

    estudiantes_demostracion = [
        ("UPEC-2026-001", "Reina Gordon Jhoel Sebastian"),
        ("UPEC-2026-002", "Cadena Edelina"),
        ("UPEC-2026-003", "Lema Jordy"),
        ("UPEC-2026-004", "Ponce Melisa"),
        ("UPEC-2026-005", "Carlosama Daniel"),
        ("UPEC-2026-006", "Montenegro Valeria"),
    ]
    cursor.executemany(
        """
        UPDATE estudiantes SET activo = 0
        WHERE codigo_estudiantil = ? AND nombre_completo = ?
          AND (foto_path IS NULL OR foto_path = '')
        """,
        estudiantes_demostracion,
    )
    cursor.execute(
        """
        UPDATE dispositivos_iot
        SET estado = 'Desconectado'
        WHERE ip_address IN (?, ?, ?)
        """,
        (
            "192.168.1.105:81",
            "127.0.0.1:5000",
            "192.168.1.120:554",
        ),
    )

    cursor.execute(
        """
        INSERT OR IGNORE INTO materia_estudiantes (materia_id, estudiante_id)
        SELECT DISTINCT a.materia_id, a.estudiante_id
        FROM asistencias a
        JOIN estudiantes e ON e.id = a.estudiante_id
        WHERE e.activo = 1
          AND a.metodo_registro != 'Regla-10min'
        """
    )

    conn.commit()
    conn.close()

_DIAS_SEMANA = (
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
)


def _normalizar_texto(texto):
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto.casefold())
        if unicodedata.category(caracter) != "Mn"
    )


def obtener_periodos_lectivos(horario, fecha):
    try:
        dia = date.fromisoformat(fecha).weekday()
    except (TypeError, ValueError) as error:
        raise ValueError("La fecha de asistencia no es válida.") from error

    periods = []
    block_index = 0
    pattern = re.compile(
        r"\b(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\s+"
        r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\b"
    )
    for line in (horario or "").splitlines():
        normalized_line = _normalizar_texto(line)
        match = pattern.search(normalized_line)
        if match is None or match.group(1) != _DIAS_SEMANA[dia]:
            continue
        if "tutoria" in normalized_line:
            continue

        start_hour, start_minute, end_hour, end_minute = map(
            int, match.groups()[1:]
        )
        start_minute_of_day = start_hour * 60 + start_minute
        end_minute_of_day = end_hour * 60 + end_minute
        if end_minute_of_day <= start_minute_of_day:
            continue

        block_index += 1
        slot_start = start_minute_of_day
        while slot_start < end_minute_of_day:
            slot_end = min(slot_start + 60, end_minute_of_day)
            periods.append({
                "indice": len(periods) + 1,
                "bloque": block_index,
                "inicio": f"{slot_start // 60:02d}:{slot_start % 60:02d}",
                "fin": f"{slot_end // 60:02d}:{slot_end % 60:02d}",
            })
            slot_start = slot_end
    return periods


def _periodo_datetime(fecha, hora):
    return datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")


def _periodo_actual(periodos, ahora):
    for periodo in periodos:
        inicio = _periodo_datetime(ahora.strftime("%Y-%m-%d"), periodo["inicio"])
        fin = _periodo_datetime(ahora.strftime("%Y-%m-%d"), periodo["fin"])
        if inicio <= ahora < fin or inicio - timedelta(minutes=10) <= ahora < inicio:
            return periodo
    return None


def _guardar_periodo(
    cursor,
    estudiante_id,
    materia_id,
    fecha,
    periodo,
    estado,
    hora,
    metodo,
    solo_si_no_existe=False,
    preservar_manual=False,
):
    sql = (
        """
        INSERT OR IGNORE INTO asistencia_periodos (
            estudiante_id, materia_id, fecha, periodo_indice, bloque_indice,
            inicio, fin, estado, hora, metodo_registro
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        if solo_si_no_existe
        else
        """
        INSERT INTO asistencia_periodos (
            estudiante_id, materia_id, fecha, periodo_indice, bloque_indice,
            inicio, fin, estado, hora, metodo_registro
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (estudiante_id, materia_id, fecha, periodo_indice)
        DO UPDATE SET bloque_indice = excluded.bloque_indice,
                      inicio = excluded.inicio,
                      fin = excluded.fin,
                      estado = excluded.estado,
                      hora = excluded.hora,
                      metodo_registro = excluded.metodo_registro
        """
        + (
            " WHERE asistencia_periodos.metodo_registro != 'Manual-Docente'"
            if preservar_manual
            else ""
        )
    )
    cursor.execute(
        sql,
        (
            estudiante_id,
            materia_id,
            fecha,
            periodo["indice"],
            periodo["bloque"],
            periodo["inicio"],
            periodo["fin"],
            estado,
            hora,
            metodo,
        ),
    )
    return cursor.rowcount > 0


def _sincronizar_asistencia_legacy(
    cursor, estudiante_id, materia_id, fecha, hora, metodo, dispositivo_id=None
):
    actual = cursor.execute(
        """
        SELECT id, hora_1_estado, hora_1_hora, hora_2_estado, hora_2_hora
        FROM asistencias
        WHERE estudiante_id = ? AND materia_id = ? AND fecha = ?
        """,
        (estudiante_id, materia_id, fecha),
    ).fetchone()
    periodos = cursor.execute(
        """
        SELECT periodo_indice, estado, hora
        FROM asistencia_periodos
        WHERE estudiante_id = ? AND materia_id = ? AND fecha = ?
        """,
        (estudiante_id, materia_id, fecha),
    ).fetchall()
    estados = {row["periodo_indice"]: row for row in periodos}

    h1 = estados.get(1)
    h2 = estados.get(2)
    h1_estado = h1["estado"] if h1 else (
        actual["hora_1_estado"] if actual else "Pendiente"
    )
    h1_hora = h1["hora"] if h1 else (
        actual["hora_1_hora"] if actual else "--:--:--"
    )
    h2_estado = h2["estado"] if h2 else (
        actual["hora_2_estado"] if actual else "Pendiente"
    )
    h2_hora = h2["hora"] if h2 else (
        actual["hora_2_hora"] if actual else "--:--:--"
    )
    estado_general = " | ".join(
        f"H{indice}: {row['estado']}"
        for indice, row in sorted(estados.items())
    ) or f"H1: {h1_estado} | H2: {h2_estado}"

    if actual:
        cursor.execute(
            """
            UPDATE asistencias
            SET estado = ?, hora = ?, metodo_registro = ?,
                dispositivo_id = COALESCE(?, dispositivo_id),
                hora_1_estado = ?, hora_1_hora = ?,
                hora_2_estado = ?, hora_2_hora = ?
            WHERE id = ?
            """,
            (
                estado_general,
                hora,
                metodo,
                dispositivo_id,
                h1_estado,
                h1_hora,
                h2_estado,
                h2_hora,
                actual["id"],
            ),
        )
    else:
        cursor.execute(
            """
            INSERT INTO asistencias (
                estudiante_id, materia_id, fecha, hora, estado, metodo_registro,
                dispositivo_id, hora_1_estado, hora_1_hora,
                hora_2_estado, hora_2_hora
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                estudiante_id,
                materia_id,
                fecha,
                hora,
                estado_general,
                metodo,
                dispositivo_id,
                h1_estado,
                h1_hora,
                h2_estado,
                h2_hora,
            ),
        )


def _aplicar_ausencias_automaticas(
    cursor, estudiante_id, materia_id, fecha, periodos, ahora
):
    if fecha != ahora.strftime("%Y-%m-%d"):
        return False

    blocks = {}
    for periodo in periodos:
        blocks.setdefault(periodo["bloque"], []).append(periodo)

    cambio = False
    for periodos_bloque in blocks.values():
        inicio_bloque = _periodo_datetime(fecha, periodos_bloque[0]["inicio"])
        fin_bloque = _periodo_datetime(fecha, periodos_bloque[-1]["fin"])
        if (
            ahora < inicio_bloque + timedelta(minutes=10)
            or ahora >= fin_bloque
        ):
            continue
        for periodo in periodos_bloque:
            cambio = _guardar_periodo(
                cursor,
                estudiante_id,
                materia_id,
                fecha,
                periodo,
                "Ausente",
                "--:--:--",
                "Regla-10min",
                solo_si_no_existe=True,
            ) or cambio
    if cambio:
        _sincronizar_asistencia_legacy(
            cursor,
            estudiante_id,
            materia_id,
            fecha,
            ahora.strftime("%H:%M:%S"),
            "Regla-10min",
        )
    return cambio


def aplicar_ausencias_programadas(ahora=None):
    ahora = ahora or datetime.now()
    fecha = ahora.strftime("%Y-%m-%d")
    conn = get_db()
    cursor = conn.cursor()
    estudiantes_actualizados = 0
    try:
        materias = cursor.execute(
            "SELECT id, horario FROM materias WHERE activo = 1"
        ).fetchall()
        for materia in materias:
            periodos = obtener_periodos_lectivos(materia["horario"], fecha)
            if not periodos:
                continue
            estudiantes = cursor.execute(
                """
                SELECT e.id
                FROM materia_estudiantes me
                JOIN estudiantes e ON e.id = me.estudiante_id
                WHERE me.materia_id = ? AND e.activo = 1
                """,
                (materia["id"],),
            ).fetchall()
            for estudiante in estudiantes:
                _migrar_asistencia_legacy(
                    cursor,
                    estudiante["id"],
                    materia["id"],
                    fecha,
                    periodos,
                )
                if _aplicar_ausencias_automaticas(
                    cursor,
                    estudiante["id"],
                    materia["id"],
                    fecha,
                    periodos,
                    ahora,
                ):
                    estudiantes_actualizados += 1
        conn.commit()
        return estudiantes_actualizados
    finally:
        conn.close()


def _migrar_asistencia_legacy(
    cursor, estudiante_id, materia_id, fecha, periodos
):
    legacy = cursor.execute(
        """
        SELECT hora_1_estado, hora_1_hora, hora_2_estado, hora_2_hora,
               metodo_registro
        FROM asistencias
        WHERE estudiante_id = ? AND materia_id = ? AND fecha = ?
        """,
        (estudiante_id, materia_id, fecha),
    ).fetchone()
    if legacy is None:
        return

    for periodo in periodos:
        indice = periodo["indice"]
        if indice not in (1, 2):
            continue
        estado = legacy[f"hora_{indice}_estado"]
        if not estado or estado == "Pendiente":
            continue
        _guardar_periodo(
            cursor,
            estudiante_id,
            materia_id,
            fecha,
            periodo,
            estado,
            legacy[f"hora_{indice}_hora"] or "--:--:--",
            legacy["metodo_registro"] or "Manual-Docente",
            solo_si_no_existe=True,
        )


def registrar_asistencia_db(
    estudiante_id,
    materia_id,
    estado="Presente",
    metodo="Facial-Carchito",
    dispositivo_id=None,
    periodo_indice=None,
):
    if isinstance(estudiante_id, bool) or not isinstance(estudiante_id, int) or estudiante_id < 1:
        raise ValueError("Selecciona un estudiante válido.")
    if isinstance(materia_id, bool) or not isinstance(materia_id, int) or materia_id < 1:
        raise ValueError("Selecciona una materia válida.")
    if not isinstance(estado, str) or estado not in {
        "Presente",
        "Ausente",
        "Atrasado",
        "Justificado",
    }:
        raise ValueError("Selecciona un estado de asistencia válido.")
    if periodo_indice is not None and (
        isinstance(periodo_indice, bool)
        or not isinstance(periodo_indice, int)
        or periodo_indice < 1
    ):
        raise ValueError("Selecciona una hora de clase válida.")

    conn = get_db()
    cursor = conn.cursor()
    try:
        inscripcion = cursor.execute(
            """
            SELECT 1 FROM materia_estudiantes
            WHERE estudiante_id = ? AND materia_id = ?
            """,
            (estudiante_id, materia_id),
        ).fetchone()
        if inscripcion is None:
            raise ValueError("El estudiante no está inscrito en la materia seleccionada.")

        ahora = datetime.now()
        fecha = ahora.strftime("%Y-%m-%d")
        hora = ahora.strftime("%H:%M:%S")
        horario = cursor.execute(
            "SELECT horario FROM materias WHERE id = ?",
            (materia_id,),
        ).fetchone()
        periodos = obtener_periodos_lectivos(
            horario["horario"] if horario else "", fecha
        )
        if not periodos:
            raise ValueError("Esta materia no tiene horas lectivas programadas para hoy.")

        _migrar_asistencia_legacy(
            cursor, estudiante_id, materia_id, fecha, periodos
        )
        _aplicar_ausencias_automaticas(
            cursor, estudiante_id, materia_id, fecha, periodos, ahora
        )

        es_escaneo_facial = "facial" in metodo.casefold()
        if es_escaneo_facial:
            periodo_actual = _periodo_actual(periodos, ahora)
            if periodo_actual is None:
                raise ValueError("El escaneo facial está fuera del horario de clase.")
            periodos_bloque = [
                periodo
                for periodo in periodos
                if periodo["bloque"] == periodo_actual["bloque"]
            ]
            inicio_bloque = _periodo_datetime(
                fecha, periodos_bloque[0]["inicio"]
            )
            if (
                periodo_actual["indice"] == periodos_bloque[0]["indice"]
                and ahora >= inicio_bloque + timedelta(minutes=10)
            ):
                raise ValueError(
                    "Ya pasaron los primeros 10 minutos de esta clase; "
                    "las faltas se mantienen. El docente puede corregirlas "
                    "hora por hora."
                )
            periodos_a_marcar = [
                periodo
                for periodo in periodos
                if periodo["bloque"] == periodo_actual["bloque"]
                and periodo["indice"] >= periodo_actual["indice"]
            ]
        else:
            if periodo_indice is None:
                periodo_actual = _periodo_actual(periodos, ahora)
                periodo_indice = (
                    periodo_actual["indice"] if periodo_actual else periodos[0]["indice"]
                )
            periodos_a_marcar = [
                periodo for periodo in periodos
                if periodo["indice"] == periodo_indice
            ]
            if not periodos_a_marcar:
                raise ValueError("La hora seleccionada no pertenece al horario de hoy.")

        for periodo in periodos_a_marcar:
            _guardar_periodo(
                cursor,
                estudiante_id,
                materia_id,
                fecha,
                periodo,
                estado,
                hora if estado != "Ausente" else "--:--:--",
                metodo,
                preservar_manual=es_escaneo_facial,
            )
        _sincronizar_asistencia_legacy(
            cursor, estudiante_id, materia_id, fecha, hora, metodo, dispositivo_id
        )
        conn.commit()
        return {
            "status": "ok",
            "fecha": fecha,
            "hora": hora,
            "estado": estado,
            "periodos_registrados": [periodo["indice"] for periodo in periodos_a_marcar],
            "metodo": metodo,
        }
    finally:
        conn.close()


def obtener_resumen_asistencia(materia_id=1, fecha=None):
    ahora = datetime.now()
    if not fecha:
        fecha = ahora.strftime("%Y-%m-%d")
    try:
        date.fromisoformat(fecha)
    except (TypeError, ValueError) as error:
        raise ValueError("La fecha de asistencia no es válida.") from error

    conn = get_db()
    cursor = conn.cursor()
    try:
        materia = cursor.execute(
            "SELECT horario FROM materias WHERE id = ?",
            (materia_id,),
        ).fetchone()
        periodos = obtener_periodos_lectivos(
            materia["horario"] if materia else "", fecha
        )
        estudiantes = cursor.execute(
            """
            SELECT e.id, e.codigo_estudiantil, e.nombre_completo,
                   e.nivel_paralelo, e.email,
                   a.estado AS estado_legacy, a.hora AS hora_legacy,
                   a.metodo_registro AS metodo_legacy,
                   a.hora_1_estado, a.hora_1_hora,
                   a.hora_2_estado, a.hora_2_hora
            FROM materia_estudiantes me
            JOIN estudiantes e ON e.id = me.estudiante_id
            LEFT JOIN asistencias a
              ON a.estudiante_id = e.id AND a.materia_id = ?
             AND a.fecha = ?
            WHERE e.activo = 1 AND me.materia_id = ?
            ORDER BY e.nombre_completo ASC
            """,
            (materia_id, fecha, materia_id),
        ).fetchall()

        for estudiante in estudiantes:
            _migrar_asistencia_legacy(
                cursor,
                estudiante["id"],
                materia_id,
                fecha,
                periodos,
            )
            _aplicar_ausencias_automaticas(
                cursor,
                estudiante["id"],
                materia_id,
                fecha,
                periodos,
                ahora,
            )
        if fecha == ahora.strftime("%Y-%m-%d"):
            conn.commit()

        detalles = cursor.execute(
            """
            SELECT estudiante_id, periodo_indice, estado, hora, metodo_registro
            FROM asistencia_periodos
            WHERE materia_id = ? AND fecha = ?
            """,
            (materia_id, fecha),
        ).fetchall()
        detalle_por_estudiante = {}
        for detalle in detalles:
            detalle_por_estudiante.setdefault(
                detalle["estudiante_id"], {}
            )[detalle["periodo_indice"]] = detalle

        registros = []
        for row in estudiantes:
            estudiante = dict(row)
            for campo, valor in (
                ("hora_1_estado", "Pendiente"),
                ("hora_1_hora", "--:--:--"),
                ("hora_2_estado", "Pendiente"),
                ("hora_2_hora", "--:--:--"),
            ):
                if estudiante[campo] is None:
                    estudiante[campo] = valor
            detalle = detalle_por_estudiante.get(estudiante["id"], {})
            estados_periodo = []
            horas_registradas = []
            metodos = []
            periodos_estudiante = []
            for periodo in periodos:
                periodo_estudiante = dict(periodo)
                guardado = detalle.get(periodo["indice"])
                estado_periodo = guardado["estado"] if guardado else "Pendiente"
                hora_periodo = guardado["hora"] if guardado else "--:--:--"
                metodo_periodo = guardado["metodo_registro"] if guardado else ""

                if guardado is None and periodo["indice"] in (1, 2):
                    sufijo = periodo["indice"]
                    legacy_estado = estudiante.get(f"hora_{sufijo}_estado")
                    if legacy_estado and legacy_estado != "Pendiente":
                        estado_periodo = legacy_estado
                        hora_periodo = estudiante.get(
                            f"hora_{sufijo}_hora"
                        ) or "--:--:--"
                        metodo_periodo = estudiante.get("metodo_legacy") or ""

                estados_periodo.append(estado_periodo)
                if hora_periodo != "--:--:--":
                    horas_registradas.append(hora_periodo)
                if metodo_periodo:
                    metodos.append(metodo_periodo)
                periodo_estudiante["estado"] = estado_periodo
                periodo_estudiante["hora"] = hora_periodo
                periodo_estudiante["metodo"] = (
                    metodo_periodo or "No registrado"
                )
                periodos_estudiante.append(periodo_estudiante)

            registrados = [
                estado for estado in estados_periodo
                if estado != "Pendiente"
            ]
            tiene_asistencia = any(
                estado in ("Presente", "Atrasado", "Justificado")
                for estado in registrados
            )
            tiene_falta = "Ausente" in registrados
            if tiene_asistencia and tiene_falta:
                estado_general = "Parcial"
            elif any(estado == "Presente" for estado in registrados):
                estado_general = "Presente"
            elif any(estado == "Atrasado" for estado in registrados):
                estado_general = "Atrasado"
            elif any(estado == "Justificado" for estado in registrados):
                estado_general = "Justificado"
            elif tiene_falta:
                estado_general = "Ausente"
            else:
                estado_general = "Pendiente"

            estudiante["estado"] = estado_general
            estudiante["hora"] = (
                max(horas_registradas)
                if horas_registradas
                else estudiante.get("hora_legacy") or "--:--:--"
            )
            estudiante["metodo"] = (
                metodos[-1]
                if metodos
                else estudiante.get("metodo_legacy") or "No registrado"
            )
            estudiante["periodos"] = periodos_estudiante
            registros.append(estudiante)
        return registros
    finally:
        conn.close()

def obtener_materias_docente(docente_id=1):
    conn = get_db()
    cursor = conn.cursor()
    administrador = cursor.execute(
        """
        SELECT id FROM docentes
        WHERE LOWER(email_institucional) = LOWER('admin@upec.edu.ec')
        """
    ).fetchone()
    if administrador and docente_id == administrador["id"]:
        cursor.execute("""
        SELECT id, codigo_materia, nombre_materia, docente_nombre, horario,
               aula, periodo, nivel_paralelo
        FROM materias
        WHERE activo = 1
        ORDER BY id
        """)
    else:
        cursor.execute("""
        SELECT id, codigo_materia, nombre_materia, docente_nombre, horario,
               aula, periodo, nivel_paralelo
        FROM materias
        WHERE docente_id = ? AND activo = 1
        ORDER BY id
        """, (docente_id,))
    materias = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return materias

def obtener_dispositivos_iot():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, nombre, tipo, ip_address, aula, estado, ultima_actividad
    FROM dispositivos_iot
    WHERE ip_address NOT IN (
        '192.168.1.105:81',
        '127.0.0.1:5000',
        '192.168.1.120:554'
    )
    """)
    dispositivos = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return dispositivos

def inscribir_estudiante_en_materia(cursor, estudiante_id, materia_id):
    cursor.execute(
        """
        INSERT OR IGNORE INTO materia_estudiantes (materia_id, estudiante_id)
        VALUES (?, ?)
        """,
        (materia_id, estudiante_id),
    )
