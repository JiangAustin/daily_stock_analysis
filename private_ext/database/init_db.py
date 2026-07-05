import sqlite3
from pathlib import Path

from private_ext.config import Settings, settings


RESEARCH_RUNS_COLUMNS = {
    "run_mode": "TEXT",
    "file_run_id": "TEXT",
    "run_dir": "TEXT",
}


def init_db(config: Settings = settings) -> Path:
    config.db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path = Path(__file__).with_name("schema.sql")
    with sqlite3.connect(config.db_path) as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        _ensure_columns(conn, "research_runs", RESEARCH_RUNS_COLUMNS)
    return config.db_path


def _ensure_columns(conn: sqlite3.Connection, table_name: str, columns: dict[str, str]) -> None:
    existing = {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, column_type in columns.items():
        if column_name in existing:
            continue
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
