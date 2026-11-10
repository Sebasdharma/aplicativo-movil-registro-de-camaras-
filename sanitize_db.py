import sqlite3

db_path = r'aplicativo-movil-registro-de-camaras--main\backend_vision\data\buhopass.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

materias = [
    (1, 'COMP-701', 'Aplicaciones Moviles', 'Lascano Samuel', 'Martes 10:00-13:00 clase\nMiercoles 10:00-11:00 tutoria\nJueves 10:00-13:00 clase', 'Lab. Computacion 3', '2026-B', 'Septimo A - Manana'),
    (2, 'COMP-702', 'Vision por Computador', 'Jimenez Stalin', 'Miercoles 09:00-10:00 tutoria\nViernes 11:00-13:00 clase', 'Lab. Computacion 3', '2026-B', 'Septimo A - Manana'),
    (3, 'COMP-703', 'Seguridad Informatica', 'Hidalgo Jairo', 'Jueves 09:00-10:00 tutoria\nViernes 08:00-11:00 clase', 'Lab. Computacion 3', '2026-B', 'Septimo A - Manana'),
    (4, 'COMP-704', 'Normativas de Ingenieria de Software', 'Lascano Samuel', 'Lunes 10:00-12:00 clase\nLunes 12:00-13:00 tutoria\nMiercoles 11:00-13:00 clase', 'Lab. Computacion 3', '2026-B', 'Septimo A - Manana'),
    (5, 'COMP-705', 'Redes de Computadoras y Seguridades', 'Del Hierro Milton', 'Martes 07:00-09:00 clase\nMartes 09:00-10:00 tutoria\nJueves 07:00-09:00 clase', 'Lab. Computacion 3', '2026-B', 'Septimo A - Manana')
]

for m in materias:
    cur.execute('''
        UPDATE materias
        SET nombre_materia = ?, docente_nombre = ?, horario = ?, aula = ?, periodo = ?, nivel_paralelo = ?
        WHERE id = ?
    ''', (m[2], m[3], m[4], m[5], m[6], m[7], m[0]))

conn.commit()
print("Materias actualizadas exitosamente:")
for row in cur.execute("SELECT id, nombre_materia, horario FROM materias"):
    print(row)
conn.close()
