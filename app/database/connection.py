
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

configured_path = Path(
    os.getenv("DATABASE_PATH", "data/emporio_musica.db")
)

DB_PATH = (
    configured_path
    if configured_path.is_absolute()
    else PROJECT_ROOT / configured_path
)

DATA_DIR = PROJECT_ROOT / "data"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    # Ativa a integridade dos relacionamentos
    connection.execute("PRAGMA foreign_keys = ON")

    return connection
