import sqlite3
from pathlib import Path

from private_ext.config import Settings, settings


def init_db(config: Settings = settings) -> Path:
    config.db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path = Path(__file__).with_name("schema.sql")
    with sqlite3.connect(config.db_path) as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
    return config.db_path

