import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "buhopass.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Tabla de Estudiantes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS estudiantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_estudiantil TEXT UNIQUE NOT NULL,
        nombre_completo TEXT NOT NULL,
        nivel_paralelo TEXT NOT NULL,
        foto_path TEXT,
        activo INTEGER DEFAULT 1
    )
    """)
    
    # Tabla de Materias
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS materias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_materia TEXT UNIQUE NOT NULL,
        nombre_materia TEXT NOT NULL,
        docente TEXT NOT NULL,
        horario TEXT
    )
    """)
    
    # Tabla de Registros de Asistencia
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS asistencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER NOT NULL,
        materia_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        hora TEXT NOT NULL,
        estado TEXT NOT NULL, -- 'Presente', 'Atrasado', 'Ausente', 'Manual'
        metodo_registro TEXT DEFAULT 'Facial-Carchito',
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes (id),
        FOREIGN KEY (materia_id) REFERENCES materias (id)
    )
    """)
    conn.commit()
    
    # Insertar datos semilla si está vacía
    cursor.execute("SELECT COUNT(*) FROM estudiantes")
    if cursor.fetchone()[0] == 0:
        estudiantes_semilla = [
            ("UPEC-2026-001", "Reina Gordon Jhoel Sebastian", "7mo Semestre - Paralelo AM"),
            ("UPEC-2026-002", "Cadena Edelina", "7mo Semestre - Paralelo AM"),
            ("UPEC-2026-003", "Lema Jordy", "7mo Semestre - Paralelo AM"),
            ("UPEC-2026-004", "Ponce Melisa", "7mo Semestre - Paralelo AM"),
            ("UPEC-2026-005", "Carlosama Daniel", "7mo Semestre - Paralelo AM"),
            ("UPEC-2026-006", "Montenegro Valeria", "7mo Semestre - Paralelo AM")
        ]
        cursor.executemany("INSERT INTO estudiantes (codigo_estudiantil, nombre_completo, nivel_paralelo) VALUES (?, ?, ?)", estudiantes_semilla)
        
        materias_semilla = [
            ("COMP-701", "Aplicaciones Móviles", "Ing. Samuel Lascano", "Lunes y Miércoles 07:00 - 09:00"),
            ("COMP-702", "Visión por Computador", "Ing. Docente Visión", "Martes y Jueves 09:00 - 11:00"),
            ("COMP-703", "Seguridad Informática", "Ing. Docente Ciberseguridad", "Viernes 07:00 - 11:00")
        ]
        cursor.executemany("INSERT INTO materias (codigo_materia, nombre_materia, docente, horario) VALUES (?, ?, ?, ?)", materias_semilla)
        
        conn.commit()
        print("¡Base de datos BúhoPass inicializada con datos semilla de la UPEC!")
    conn.close()

def registrar_asistencia_db(estudiante_id, materia_id, estado="Presente", metodo="Facial-Carchito"):
    conn = get_db()
    cursor = conn.cursor()
    hoy = datetime.now().strftime("%Y-%m-%d")
    hora = datetime.now().strftime("%H:%M:%S")
    
    # Verificar si ya tiene asistencia hoy en esta materia
    cursor.execute("SELECT id FROM asistencias WHERE estudiante_id = ? AND materia_id = ? AND fecha = ?", (estudiante_id, materia_id, hoy))
    existe = cursor.fetchone()
    if existe:
        cursor.execute("UPDATE asistencias SET estado = ?, hora = ?, metodo_registro = ? WHERE id = ?", (estado, hora, metodo, existe['id']))
    else:
        cursor.execute("INSERT INTO asistencias (estudiante_id, materia_id, fecha, hora, estado, metodo_registro) VALUES (?, ?, ?, ?, ?, ?)", 
                       (estudiante_id, materia_id, hoy, hora, estado, metodo))
    conn.commit()
    conn.close()
    return {"status": "ok", "fecha": hoy, "hora": hora, "estado": estado}

def obtener_resumen_asistencia(materia_id=1):
    conn = get_db()
    cursor = conn.cursor()
    hoy = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute("""
    SELECT e.id, e.codigo_estudiantil, e.nombre_completo, e.nivel_paralelo,
           COALESCE(a.estado, 'Ausente') as estado,
           COALESCE(a.hora, '--:--:--') as hora,
           COALESCE(a.metodo_registro, 'No registrado') as metodo
    FROM estudiantes e
    LEFT JOIN asistencias a ON e.id = a.estudiante_id AND a.materia_id = ? AND a.fecha = ?
    WHERE e.activo = 1
    ORDER BY e.nombre_completo ASC
    """, (materia_id, hoy))
    
    registros = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return registros
