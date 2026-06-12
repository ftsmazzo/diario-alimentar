# -*- coding: utf-8 -*-
"""Aguarda o PostgreSQL ficar disponível antes das migrations."""
import os
import time

from sqlalchemy import create_engine, text


def _database_url():
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def wait(max_attempts=30, delay=2):
    url = _database_url()
    if not url or url.startswith("sqlite"):
        return

    for attempt in range(1, max_attempts + 1):
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Banco de dados disponível.")
            return
        except Exception:
            print(f"Aguardando banco... ({attempt}/{max_attempts})")
            time.sleep(delay)

    raise RuntimeError("Banco de dados indisponível após várias tentativas.")


if __name__ == "__main__":
    wait()
