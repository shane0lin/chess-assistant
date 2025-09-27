"""SQLite helpers for chessassistant runtime."""
from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Optional


_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DB_PATH = _REPO_ROOT / "resources" / "chessassistant.db"


def get_connection(db_path: Optional[Path | str] = None) -> sqlite3.Connection:
    """Return a SQLite connection, creating parent directories as needed."""
    path = Path(db_path) if db_path else _DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Ensure the core tables exist and migrate existing schemas."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tournament_players (
            universal_tournament_id TEXT NOT NULL,
            universal_player_id TEXT NOT NULL,
            source TEXT NOT NULL,
            source_tournament_id TEXT NOT NULL,
            player_name TEXT NOT NULL,
            session_name TEXT NOT NULL,
            uscf_id TEXT,
            uscf_rating INTEGER,
            nwsrs_id TEXT,
            nwsrs_rating INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (universal_tournament_id, universal_player_id)
        )
        """
    )

    # Migrate existing tables to add NWSRS columns if missing
    _migrate_tournament_players_table(connection)
    connection.commit()


def ensure_database(db_path: Optional[Path | str] = None) -> sqlite3.Connection:
    """Create the database (if missing) and ensure schema is initialized."""
    connection = get_connection(db_path=db_path)
    initialize_schema(connection)
    return connection


def _migrate_tournament_players_table(connection: sqlite3.Connection) -> None:
    """Add NWSRS columns to existing tournament_players table if missing."""
    # Check if nwsrs_id column exists
    cursor = connection.cursor()
    cursor.execute("PRAGMA table_info(tournament_players)")
    columns = [row[1] for row in cursor.fetchall()]

    if "nwsrs_id" not in columns:
        connection.execute("ALTER TABLE tournament_players ADD COLUMN nwsrs_id TEXT")

    if "nwsrs_rating" not in columns:
        connection.execute("ALTER TABLE tournament_players ADD COLUMN nwsrs_rating INTEGER")
