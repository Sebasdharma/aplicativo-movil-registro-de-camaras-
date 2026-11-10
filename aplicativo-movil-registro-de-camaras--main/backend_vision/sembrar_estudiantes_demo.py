"""Carga los estudiantes de demostración (el equipo del proyecto).

Crea o reactiva a cada estudiante de database.ESTUDIANTES_DEMOSTRACION, lo
inscribe en las materias activas y registra su foto facial si el archivo está
en dataset_estudiantes/. Funciona con SQLite y con Supabase (DATABASE_URL).

Uso (desde la carpeta backend_vision):

    python sembrar_estudiantes_demo.py
    python sembrar_estudiantes_demo.py --materia 1 --materia 2   # solo esas materias

Se puede ejecutar varias veces: no duplica estudiantes, inscripciones ni fotos.
"""

import argparse
import os

import database

DATASET_DIR = os.path.join(database._BASE_DIR, "dataset_estudiantes")


def sembrar(materias=None):
    database.init_db()
    conn = database.get_db()
    cursor = conn.cursor()
    resumen = []
    try:
        ids_materias = [
            row["id"]
            for row in cursor.execute(
                "SELECT id FROM materias WHERE activo = 1 ORDER BY id"
            ).fetchall()
            if not materias or row["id"] in materias
        ]

        for codigo, nombre, paralelo, email, foto in database.ESTUDIANTES_DEMOSTRACION:
            foto_disponible = bool(foto) and os.path.isfile(os.path.join(DATASET_DIR, foto))
            existente = cursor.execute(
                "SELECT id FROM estudiantes WHERE codigo_estudiantil = ?",
                (codigo,),
            ).fetchone()
            if existente:
                estudiante_id = existente["id"]
                cursor.execute(
                    """
                    UPDATE estudiantes
                    SET nombre_completo = ?, nivel_paralelo = ?, email = ?, activo = 1
                    WHERE id = ?
                    """,
                    (nombre, paralelo, email, estudiante_id),
                )
            else:
                estudiante_id = database.insertar_y_obtener_id(
                    cursor,
                    """
                    INSERT INTO estudiantes
                        (codigo_estudiantil, nombre_completo, nivel_paralelo, email, activo)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (codigo, nombre, paralelo, email),
                )
            for materia_id in ids_materias:
                database.inscribir_estudiante_en_materia(cursor, estudiante_id, materia_id)
            if foto_disponible:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO fotos_faciales_estudiantes (estudiante_id, foto_path)
                    VALUES (?, ?)
                    """,
                    (estudiante_id, foto),
                )
            estado_foto = (
                "foto registrada" if foto_disponible
                else "sin foto" if not foto
                else f"falta el archivo {foto}"
            )
            resumen.append((codigo, nombre, estado_foto))
        conn.commit()
    finally:
        conn.close()

    destino = "Supabase/PostgreSQL" if database.usando_postgres() else "SQLite local"
    print(f"Estudiantes de demostración cargados en {destino} "
          f"e inscritos en {len(ids_materias)} materia(s):")
    for codigo, nombre, estado_foto in resumen:
        print(f"  {codigo}  {nombre:<32} {estado_foto}")
    return resumen


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--materia",
        type=int,
        action="append",
        help="ID de materia donde inscribirlos (se puede repetir). Por defecto: todas las activas.",
    )
    args = parser.parse_args(argv)
    sembrar(args.materia)


if __name__ == "__main__":
    main()
