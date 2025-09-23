from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from src.agents.crawlers.nwchess import NwChessRosterCrawler
from src.common import db as db_module


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl an NWChess roster URL and persist entries to SQLite."
    )
    parser.add_argument(
        "url",
        help="NWChess roster URL (e.g. https://nwchess.com/OnlineRegistration/roster.php?tournamentid=977)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Optional path to the SQLite database file (defaults to resources/chessassistant.db)",
    )
    return parser.parse_args(argv)


def run(url: str, db_path: Optional[Path]) -> int:
    crawler = NwChessRosterCrawler()
    connection = db_module.ensure_database(db_path)
    try:
        entries = crawler.crawl(url, connection=connection)
        db_info = connection.execute("PRAGMA database_list").fetchone()
    except Exception as exc:
        print(f"Error crawling {url}: {exc}", file=sys.stderr)
        return 1
    finally:
        connection.close()

    db_file = db_info["file"] if db_info is not None else ""
    target_db: Path | str
    if db_file:
        target_db = Path(db_file)
    elif db_path is not None:
        target_db = db_path
    else:
        target_db = "<in-memory>"

    print(f"Persisted {len(entries)} roster entries into {target_db}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    return run(args.url, args.db_path)


if __name__ == "__main__":
    sys.exit(main())
