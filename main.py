from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from src.agents.crawlers.nwchess import NwChessRosterCrawler
from src.common import db as db_module
from src.common import exports


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
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("resources/reports"),
        help="Directory for CSV and HTML output files (defaults to resources/reports)",
    )
    return parser.parse_args(argv)


def run(url: str, db_path: Optional[Path], output_dir: Path) -> int:
    crawler = NwChessRosterCrawler()
    connection = db_module.ensure_database(db_path)
    try:
        entries = crawler.crawl(url, connection=connection)
        db_info = connection.execute("PRAGMA database_list").fetchone()

        # Generate exports
        tournament_id = crawler._extract_tournament_id(url)
        filename = exports.get_tournament_filename(url, tournament_id)

        csv_path = output_dir / f"{filename}.csv"
        html_path = output_dir / f"{filename}.html"

        exports.export_to_csv(entries, csv_path)
        exports.export_to_html(entries, html_path, tournament_id)
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
    print(f"Exported CSV to: {csv_path}")
    print(f"Exported HTML to: {html_path}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    return run(args.url, args.db_path, args.output_dir)


if __name__ == "__main__":
    sys.exit(main())
