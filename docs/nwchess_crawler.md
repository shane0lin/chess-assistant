# NWChess Roster Crawler

This module ingests NWChess online registration rosters and normalizes them
into the `tournament_players` SQLite table under `resources/chessassistant.db`.

## Usage

```python
from src.agents.crawlers.nwchess import NwChessRosterCrawler
from src.common.db import ensure_database

crawler = NwChessRosterCrawler()
connection = ensure_database()
try:
    entries = crawler.crawl(
        "https://nwchess.com/OnlineRegistration/roster.php?tournamentid=977",
        connection=connection,
    )
    print(f"Persisted {len(entries)} NWChess players")
finally:
    connection.close()
```

The composite primary key for the table is the pair of the universal tournament
ID (deterministically derived from the source tournament ID) and the universal
player ID (derived from the tournament namespace and either the player's
USCF ID or full name).

## Development Notes

* Install dependencies with `pip install -r requirements.txt`.
* Run the crawler tests via `pytest tests/agents/crawlers/test_nwchess.py`.
* Sample HTML fixtures live in `tests/fixtures/` for deterministic testing.
* The crawler gracefully upserts entries so repeated runs keep the table fresh
  without duplicating rows.
