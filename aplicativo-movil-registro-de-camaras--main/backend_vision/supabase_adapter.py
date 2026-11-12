import os
import pathlib
import re
import psycopg


def _load_local_env():
    env_file = pathlib.Path(__file__).resolve().parent / ".env"
    if not env_file.is_file():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env()

SUPABASE_DB_URL = (
    os.environ.get("SUPABASE_DB_URL")
    or os.environ.get("DATABASE_URL")
    or ""
)

class RowWrapper(dict):
    """
    Fila híbrida compatible con sqlite3.Row:
    Permite acceso por nombre: row['nombre']
    Permite acceso por índice: row[0]
    Permite conversión a dict: dict(row)
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._keys = list(self.keys())

    def __getitem__(self, key):
        if isinstance(key, int):
            return super().__getitem__(self._keys[key])
        return super().__getitem__(key)

    def get(self, key, default=None):
        if isinstance(key, int):
            try:
                return super().__getitem__(self._keys[key])
            except (IndexError, KeyError):
                return default
        return super().get(key, default)


def hybrid_row_factory(cursor):
    names = [col.name for col in cursor.description] if cursor.description else []
    def make_row(values):
        return RowWrapper(zip(names, values))
    return make_row


class PgCursorWrapper:
    def __init__(self, cur):
        self._cur = cur
        self.lastrowid = None

    def execute(self, query, params=None):
        # 1. Convertir placeholders de SQLite (?) a PostgreSQL (%s)
        clean_query = query.replace("?", "%s")

        # 2. Convertir INSERT OR IGNORE a ON CONFLICT DO NOTHING
        if "INSERT OR IGNORE INTO" in clean_query:
            clean_query = clean_query.replace("INSERT OR IGNORE INTO", "INSERT INTO")
            if "ON CONFLICT" not in clean_query.upper():
                clean_query += " ON CONFLICT DO NOTHING"

        # 3. Soporte para lastrowid en INSERTs que no tengan ON CONFLICT
        is_insert = clean_query.strip().upper().startswith("INSERT INTO")
        has_on_conflict = "ON CONFLICT" in clean_query.upper()
        if is_insert and not has_on_conflict and "RETURNING" not in clean_query.upper():
            clean_query += " RETURNING id"
            self._cur.execute(clean_query, params or ())
            try:
                row = self._cur.fetchone()
                if row:
                    self.lastrowid = row[0] if isinstance(row, (tuple, list)) else row.get("id") or row.get(0)
            except Exception:
                pass
            return self

        self._cur.execute(clean_query, params or ())
        return self

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def __iter__(self):
        return iter(self._cur)

    def close(self):
        self._cur.close()


class PgConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return PgCursorWrapper(self._conn.cursor(row_factory=hybrid_row_factory))

    def execute(self, query, params=None):
        cur = self.cursor()
        return cur.execute(query, params)

    def commit(self):
        if not getattr(self._conn, "autocommit", False):
            self._conn.commit()

    def rollback(self):
        if not getattr(self._conn, "autocommit", False):
            self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()


def get_supabase_connection():
    db_url = (
        os.environ.get("SUPABASE_DB_URL")
        or os.environ.get("DATABASE_URL")
        or SUPABASE_DB_URL
    )
    if not db_url:
        raise RuntimeError(
            "Configura SUPABASE_DB_URL o DATABASE_URL para conectar con Supabase."
        )
    raw = psycopg.connect(
        db_url,
        connect_timeout=10,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
        autocommit=True,
    )
    return PgConnectionWrapper(raw)

