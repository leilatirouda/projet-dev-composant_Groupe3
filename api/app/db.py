"""Accès à PostgreSQL (psycopg 3, requêtes paramétrées)."""
import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://sante:sante@localhost:5432/sante_db"
)
CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "3"))


class DatabaseUnavailable(Exception):
    """La base ne répond pas (arrêt, réseau, identifiants)."""


@contextmanager
def get_conn():
    try:
        conn = psycopg.connect(
            DATABASE_URL, row_factory=dict_row, connect_timeout=CONNECT_TIMEOUT
        )
    except psycopg.OperationalError as exc:
        raise DatabaseUnavailable(str(exc)) from exc
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(sql: str, params: dict) -> list[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def fetch_one(sql: str, params: dict) -> dict | None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def ping() -> bool:
    try:
        fetch_one("SELECT 1 AS ok", {})
        return True
    except DatabaseUnavailable:
        return False
