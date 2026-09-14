"""
Small shared helper for opening SQLite connections and applying schema files.
Used by seed scripts, the mediator, ETL, and DWH modules alike.
"""
import sqlite3
import config


def get_connection(db_path: str) -> sqlite3.Connection:
    """Open a connection to one of the independent SQLite databases."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")  # each DB is independent, no cross-db FKs
    return conn


def run_script(db_path: str, sql_path: str) -> None:
    """Execute a .sql schema file against a database (creates/recreates tables)."""
    with open(sql_path, "r", encoding="utf-8") as f:
        script = f.read()
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(script)
        conn.commit()
    finally:
        conn.close()


def init_all_schemas() -> None:
    """(Re)create every table in every database from its schema file."""
    for db_path, schema_path in config.SCHEMA_FILES.items():
        run_script(db_path, schema_path)
        print(f"[schema] applied {schema_path} -> {db_path}")


if __name__ == "__main__":
    init_all_schemas()
