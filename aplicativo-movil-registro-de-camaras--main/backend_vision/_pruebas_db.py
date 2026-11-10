"""Aísla las pruebas de la base de datos real.

Se importa antes que ``database`` en cada archivo de pruebas. Por defecto las
pruebas usan archivos SQLite temporales, aunque exista un ``.env`` con la
DATABASE_URL de Supabase. Para ejecutar las mismas pruebas contra un
PostgreSQL desechable, define ASISTECH_TEST_DATABASE_URL (todas sus tablas se
borran antes de cada prueba).
"""

import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
URL_PRUEBAS = os.environ.get("ASISTECH_TEST_DATABASE_URL", "").strip()


def _url_real_configurada():
    url = os.environ.get("DATABASE_URL", "").strip()
    try:
        from dotenv import dotenv_values
    except ImportError:
        return url
    return url or (dotenv_values(os.path.join(_BASE_DIR, ".env")).get("DATABASE_URL") or "").strip()


if URL_PRUEBAS and URL_PRUEBAS == _url_real_configurada():
    raise RuntimeError(
        "ASISTECH_TEST_DATABASE_URL no puede ser la misma base que DATABASE_URL: "
        "las pruebas borran todas las tablas."
    )

# load_dotenv no sobrescribe variables existentes, así que esto evita que
# database.py tome la DATABASE_URL real del archivo .env.
os.environ["DATABASE_URL"] = URL_PRUEBAS

import database  # noqa: E402

database.DATABASE_URL = URL_PRUEBAS


def reiniciar_base_postgres():
    """Deja vacía la base PostgreSQL de pruebas (no hace nada con SQLite)."""
    if not URL_PRUEBAS:
        return
    conn = database.get_db()
    try:
        for tabla in reversed(database.TABLAS):
            conn.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")
        conn.commit()
    finally:
        conn.close()
