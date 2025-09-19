#!/usr/bin/env python3
"""check_pg_conn.py

Simple utility to test the Postgres connection string used by the app.
Reads PG_CONN from environment (preferred) or from settings.json under key "pg_conn".
Usage:
    python check_pg_conn.py
    PG_CONN="postgresql+psycopg://..." python check_pg_conn.py
    python check_pg_conn.py --conn "postgresql+psycopg://..."

Exit code: 0 on success, non-zero on failure.
"""
import os
import sys
import json
import argparse
import traceback

try:
    from sqlalchemy import create_engine, text
except Exception:
    print("Missing dependency: sqlalchemy. Install with 'pip install SQLAlchemy psycopg2-binary'")
    sys.exit(2)


def load_settings(path="settings.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_conn_from_env_or_settings():
    conn = os.getenv("PG_CONN")
    if conn:
        return conn
    settings = load_settings()
    return settings.get("pg_conn") or settings.get("PG_CONN")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--conn", help="Postgres connection string override")
    args = p.parse_args()

    conn = args.conn or get_conn_from_env_or_settings()
    if not conn:
        print("No PG_CONN found in environment or settings.json. Set PG_CONN or pass --conn.")
        sys.exit(3)

    print(f"Testing PG connection: {conn}")

    try:
        engine = create_engine(conn, connect_args={}, pool_pre_ping=True)
        with engine.connect() as conn_ctx:
            # Try a lightweight test; prefer SELECT 1
            result = conn_ctx.execute(text("SELECT 1"))
            val = result.scalar()
            print("Connection test successful. SELECT 1 ->", val)
        engine.dispose()
        sys.exit(0)
    except Exception as e:
        print("Connection test failed:")
        traceback.print_exc()
        sys.exit(4)


if __name__ == '__main__':
    main()
