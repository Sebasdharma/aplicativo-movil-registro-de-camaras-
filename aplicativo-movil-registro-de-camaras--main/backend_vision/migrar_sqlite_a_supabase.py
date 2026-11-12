import sqlite3
import os
import psycopg
from psycopg.rows import dict_row

from supabase_adapter import SUPABASE_DB_URL

SUPABASE_URL = SUPABASE_DB_URL or os.environ.get("DATABASE_URL", "")
SQLITE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "buhopass.db")

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS docentes (
        id SERIAL PRIMARY KEY,
        email_institucional TEXT UNIQUE NOT NULL,
        nombre_completo TEXT NOT NULL,
        cedula TEXT,
        facultad TEXT NOT NULL,
        carrera TEXT NOT NULL,
        auth_provider TEXT DEFAULT 'microsoft'
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS materias (
        id SERIAL PRIMARY KEY,
        codigo_materia TEXT UNIQUE NOT NULL,
        nombre_materia TEXT NOT NULL,
        docente_id INTEGER REFERENCES docentes(id) ON DELETE SET NULL,
        docente_nombre TEXT NOT NULL,
        horario TEXT,
        aula TEXT DEFAULT 'Lab. Computación 3',
        periodo TEXT DEFAULT '2026-B',
        nivel_paralelo TEXT DEFAULT 'Séptimo A - Mañana',
        activo INTEGER NOT NULL DEFAULT 1
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS estudiantes (
        id SERIAL PRIMARY KEY,
        codigo_estudiantil TEXT UNIQUE NOT NULL,
        nombre_completo TEXT NOT NULL,
        nivel_paralelo TEXT NOT NULL,
        email TEXT,
        foto_path TEXT,
        activo INTEGER DEFAULT 1
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS materia_estudiantes (
        materia_id INTEGER NOT NULL REFERENCES materias(id) ON DELETE CASCADE,
        estudiante_id INTEGER NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
        fecha_inscripcion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (materia_id, estudiante_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS fotos_faciales_estudiantes (
        id SERIAL PRIMARY KEY,
        estudiante_id INTEGER NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
        foto_path TEXT NOT NULL UNIQUE,
        fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_fotos_faciales_estudiante
    ON fotos_faciales_estudiantes (estudiante_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS dispositivos_iot (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        tipo TEXT NOT NULL,
        ip_address TEXT,
        aula TEXT NOT NULL,
        estado TEXT DEFAULT 'Conectado',
        ultima_actividad TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS asistencias (
        id SERIAL PRIMARY KEY,
        estudiante_id INTEGER NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
        materia_id INTEGER NOT NULL REFERENCES materias(id) ON DELETE CASCADE,
        fecha TEXT NOT NULL,
        estado TEXT NOT NULL,
        hora TEXT NOT NULL,
        metodo_registro TEXT DEFAULT 'Facial-Carchito',
        dispositivo_id INTEGER REFERENCES dispositivos_iot(id) ON DELETE SET NULL,
        hora_1_estado TEXT DEFAULT 'Pendiente',
        hora_1_hora TEXT DEFAULT '--:--:--',
        hora_2_estado TEXT DEFAULT 'Pendiente',
        hora_2_hora TEXT DEFAULT '--:--:--'
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS asistencia_periodos (
        estudiante_id INTEGER NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
        materia_id INTEGER NOT NULL REFERENCES materias(id) ON DELETE CASCADE,
        fecha TEXT NOT NULL,
        periodo_indice INTEGER NOT NULL,
        bloque_indice INTEGER NOT NULL,
        inicio TEXT NOT NULL,
        fin TEXT NOT NULL,
        estado TEXT NOT NULL,
        hora TEXT NOT NULL DEFAULT '--:--:--',
        metodo_registro TEXT NOT NULL,
        PRIMARY KEY (estudiante_id, materia_id, fecha, periodo_indice)
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_asistencia_periodos_materia_fecha
    ON asistencia_periodos (materia_id, fecha, periodo_indice);
    """
]

TABLE_CONFIGS = [
    {
        "name": "docentes",
        "columns": ["id", "email_institucional", "nombre_completo", "cedula", "facultad", "carrera", "auth_provider"],
        "has_seq": True
    },
    {
        "name": "materias",
        "columns": ["id", "codigo_materia", "nombre_materia", "docente_id", "docente_nombre", "horario", "aula", "periodo", "nivel_paralelo", "activo"],
        "has_seq": True
    },
    {
        "name": "estudiantes",
        "columns": ["id", "codigo_estudiantil", "nombre_completo", "nivel_paralelo", "email", "foto_path", "activo"],
        "has_seq": True
    },
    {
        "name": "materia_estudiantes",
        "columns": ["materia_id", "estudiante_id", "fecha_inscripcion"],
        "has_seq": False
    },
    {
        "name": "fotos_faciales_estudiantes",
        "columns": ["id", "estudiante_id", "foto_path", "fecha_registro"],
        "has_seq": True
    },
    {
        "name": "dispositivos_iot",
        "columns": ["id", "nombre", "tipo", "ip_address", "aula", "estado", "ultima_actividad"],
        "has_seq": True
    },
    {
        "name": "asistencias",
        "columns": ["id", "estudiante_id", "materia_id", "fecha", "estado", "hora", "metodo_registro", "dispositivo_id", "hora_1_estado", "hora_1_hora", "hora_2_estado", "hora_2_hora"],
        "has_seq": True
    },
    {
        "name": "asistencia_periodos",
        "columns": ["estudiante_id", "materia_id", "fecha", "periodo_indice", "bloque_indice", "inicio", "fin", "estado", "hora", "metodo_registro"],
        "has_seq": False
    }
]

def migrar():
    print("Iniciando migración desde SQLite local a Supabase Cloud...")
    if not os.path.exists(SQLITE_DB):
        raise FileNotFoundError(f"No existe {SQLITE_DB}")

    s_conn = sqlite3.connect(SQLITE_DB)
    s_conn.row_factory = sqlite3.Row

    with psycopg.connect(SUPABASE_URL, autocommit=True) as pg_conn:
        with pg_conn.cursor() as pg_cur:
            print("1. Creando tablas en Supabase PostgreSQL...")
            for ddl in DDL_STATEMENTS:
                pg_cur.execute(ddl)
            print("   Tablas creadas / verificadas exitosamente.")

            print("2. Migrando datos tabla por tabla...")
            for config in TABLE_CONFIGS:
                table = config["name"]
                cols = config["columns"]
                cols_str = ", ".join(cols)
                placeholders = ", ".join(["%s"] * len(cols))

                # Leer de SQLite
                s_cur = s_conn.cursor()
                rows = s_cur.execute(f"SELECT {cols_str} FROM {table}").fetchall()
                if not rows:
                    print(f"   - {table}: 0 registros encontrados.")
                    continue

                # Insertar en PostgreSQL con ON CONFLICT DO NOTHING
                conflict_clause = ""
                if table == "materia_estudiantes":
                    conflict_clause = "ON CONFLICT (materia_id, estudiante_id) DO NOTHING"
                elif table == "asistencia_periodos":
                    conflict_clause = "ON CONFLICT (estudiante_id, materia_id, fecha, periodo_indice) DO NOTHING"
                elif table == "fotos_faciales_estudiantes":
                    conflict_clause = "ON CONFLICT (foto_path) DO NOTHING"
                elif "id" in cols:
                    conflict_clause = "ON CONFLICT (id) DO NOTHING"

                sql = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) {conflict_clause}"
                
                insert_count = 0
                for r in rows:
                    vals = [r[col] for col in cols]
                    pg_cur.execute(sql, vals)
                    insert_count += 1

                print(f"   [OK] {table}: {insert_count} filas migradas.")

                # Actualizar secuencia si tiene id SERIAL
                if config["has_seq"]:
                    pg_cur.execute(f"""
                        SELECT setval(
                            pg_get_serial_sequence('{table}', 'id'),
                            COALESCE(MAX(id), 1),
                            MAX(id) IS NOT NULL
                        ) FROM {table};
                    """)

            print("\n3. Verificando conteos en Supabase Cloud:")
            for config in TABLE_CONFIGS:
                table = config["name"]
                pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = pg_cur.fetchone()[0]
                print(f"   - Supabase {table}: {count} filas")

    s_conn.close()
    print("\n¡MIGRACION A SUPABASE COMPLETADA CON EXITO!")

if __name__ == "__main__":
    migrar()
