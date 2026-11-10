"""Copia los datos de la base SQLite local a PostgreSQL (Supabase).

Uso (desde la carpeta backend_vision, con DATABASE_URL configurada en .env):

    python migrar_a_supabase.py
    python migrar_a_supabase.py --sqlite data/otra_base.db
    python migrar_a_supabase.py --reemplazar   # vacía primero las tablas en la nube

El archivo SQLite solo se lee; nunca se modifica.
"""

import argparse
import os
import sqlite3
import sys

import database

# (columna, tabla_referenciada, se_puede_dejar_nula)
CLAVES_FORANEAS = {
    "materias": [("docente_id", "docentes", True)],
    "materia_estudiantes": [
        ("materia_id", "materias", False),
        ("estudiante_id", "estudiantes", False),
    ],
    "fotos_faciales_estudiantes": [("estudiante_id", "estudiantes", False)],
    "asistencias": [
        ("estudiante_id", "estudiantes", False),
        ("materia_id", "materias", False),
        ("dispositivo_id", "dispositivos_iot", True),
    ],
    "asistencia_periodos": [
        ("estudiante_id", "estudiantes", False),
        ("materia_id", "materias", False),
    ],
}
TABLAS_CON_ID = (
    "docentes",
    "materias",
    "estudiantes",
    "fotos_faciales_estudiantes",
    "dispositivos_iot",
    "asistencias",
)


def _abrir_sqlite(ruta):
    if not os.path.isfile(ruta):
        raise SystemExit(f"No se encontró la base SQLite: {ruta}")
    conn = sqlite3.connect(f"file:{os.path.abspath(ruta)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _tablas_sqlite(conn):
    return {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }


def _tipos_destino(cursor, tabla):
    return {
        row["column_name"]: row["data_type"]
        for row in cursor.execute(
            """
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_schema = current_schema() AND table_name = ?
            """,
            (tabla,),
        ).fetchall()
    }


def _convertir(valor, tipo):
    """SQLite no obliga tipos; PostgreSQL sí. Ajusta cada valor a su columna."""
    if valor is None:
        return None
    if tipo in ("integer", "bigint", "smallint"):
        if isinstance(valor, str):
            valor = valor.strip()
            return int(valor) if valor else None
        return int(valor)
    if tipo == "text" and not isinstance(valor, str):
        return str(valor)
    return valor


def _contar_filas(cursor):
    return {
        tabla: cursor.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        for tabla in database.TABLAS
    }


def migrar(ruta_sqlite, reemplazar=False):
    if not database.usando_postgres():
        raise SystemExit(
            "Falta DATABASE_URL. Copia .env.example a .env y pega la cadena de "
            "conexión de Supabase."
        )

    origen = _abrir_sqlite(ruta_sqlite)
    tablas_origen = _tablas_sqlite(origen)
    destino = database.get_db()
    cursor = destino.cursor()
    try:
        database.crear_tablas(cursor)
        destino.commit()

        existentes = {t: n for t, n in _contar_filas(cursor).items() if n}
        if existentes and not reemplazar:
            detalle = ", ".join(f"{t}={n}" for t, n in existentes.items())
            raise SystemExit(
                "La base en la nube ya tiene datos "
                f"({detalle}).\nPara borrarlos y copiar de nuevo usa: "
                "python migrar_a_supabase.py --reemplazar"
            )
        if existentes:
            cursor.execute(
                "TRUNCATE " + ", ".join(database.TABLAS) + " RESTART IDENTITY CASCADE"
            )

        ids_copiados = {}
        resumen = []
        for tabla in database.TABLAS:
            if tabla not in tablas_origen:
                resumen.append((tabla, 0, 0, "no existe en SQLite"))
                continue
            tipos = _tipos_destino(cursor, tabla)
            columnas_origen = [
                row["name"] for row in origen.execute(f"PRAGMA table_info({tabla})")
            ]
            columnas = [c for c in columnas_origen if c in tipos]
            if tabla == "materias" and "docente" in columnas_origen and "docente_nombre" not in columnas:
                columnas.append("docente_nombre")
            omitidas_columnas = [c for c in columnas_origen if c not in tipos]

            filas = []
            omitidas = 0
            for row in origen.execute(
                f"SELECT * FROM {tabla} ORDER BY rowid"
            ):
                valores = {
                    c: _convertir(row[c], tipos[c]) if c in row.keys() else None
                    for c in columnas
                }
                if (
                    tabla == "materias"
                    and "docente" in columnas_origen
                    and not valores.get("docente_nombre")
                ):
                    valores["docente_nombre"] = row["docente"]
                valida = True
                for columna, referencia, nulable in CLAVES_FORANEAS.get(tabla, []):
                    valor = valores.get(columna)
                    if valor is None or valor in ids_copiados.get(referencia, set()):
                        continue
                    if nulable:
                        valores[columna] = None
                    else:
                        valida = False
                        break
                if not valida:
                    omitidas += 1
                    continue
                filas.append(tuple(valores[c] for c in columnas))

            if filas:
                marcadores = ", ".join("?" for _ in columnas)
                cursor.executemany(
                    f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({marcadores})",
                    filas,
                )
            if "id" in columnas:
                indice_id = columnas.index("id")
                ids_copiados[tabla] = {fila[indice_id] for fila in filas}
            nota = (
                f"columnas antiguas ignoradas: {', '.join(omitidas_columnas)}"
                if omitidas_columnas
                else ""
            )
            resumen.append((tabla, len(filas), omitidas, nota))

        for tabla in TABLAS_CON_ID:
            cursor.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{tabla}', 'id'),
                    COALESCE(MAX(id), 1),
                    MAX(id) IS NOT NULL
                ) FROM {tabla}
                """
            )
        destino.commit()
    except BaseException:
        destino.rollback()
        raise
    finally:
        destino.close()
        origen.close()

    # Aplica las mismas correcciones y datos base que el servidor al iniciar.
    database.init_db()

    print(f"\nMigración completada desde {ruta_sqlite}\n")
    print(f"{'Tabla':<28}{'Copiadas':>10}{'Omitidas':>10}")
    for tabla, copiadas, omitidas, nota in resumen:
        print(f"{tabla:<28}{copiadas:>10}{omitidas:>10}  {nota}")
    if any(omitidas for _, _, omitidas, _ in resumen):
        print(
            "\nLas filas omitidas apuntaban a registros que ya no existen "
            "(por ejemplo, asistencias de un estudiante borrado)."
        )
    return resumen


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--sqlite",
        default=database.DB_PATH,
        help="Ruta de la base SQLite a copiar (por defecto data/buhopass.db).",
    )
    parser.add_argument(
        "--reemplazar",
        action="store_true",
        help="Borra los datos que ya existan en PostgreSQL antes de copiar.",
    )
    args = parser.parse_args(argv)
    migrar(args.sqlite, reemplazar=args.reemplazar)


if __name__ == "__main__":
    sys.exit(main())
