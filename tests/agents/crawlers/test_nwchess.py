import sqlite3
from pathlib import Path

import pytest

from src.agents.crawlers import nwchess
from src.common import db as db_module


@pytest.fixture
def roster_html() -> str:
    fixture_path = Path("tests/fixtures/nwchess_roster.html")
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def temp_db(tmp_path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    connection = db_module.ensure_database(db_path)
    yield connection
    connection.close()


def test_parse_and_persist_roster(monkeypatch, roster_html, temp_db):
    crawler = nwchess.NwChessRosterCrawler()
    monkeypatch.setattr(crawler, "_fetch", lambda url: roster_html)

    url = "https://nwchess.com/OnlineRegistration/roster.php?tournamentid=977"
    entries = crawler.crawl(url, connection=temp_db)

    assert len(entries) == 63
    first_entry = entries[0]
    assert first_entry.player_name == "Anirudh Raghavan"
    assert first_entry.session_name == "4-12U1000"
    assert first_entry.uscf_id == "32408975"
    assert first_entry.uscf_rating == 467

    row = temp_db.execute(
        "SELECT player_name, session_name, uscf_id, uscf_rating, source FROM tournament_players WHERE player_name = ?",
        ("Anirudh Raghavan",),
    ).fetchone()
    assert row[0] == "Anirudh Raghavan"
    assert row[1] == "4-12U1000"
    assert row[2] == "32408975"
    assert row[3] == 467
    assert row[4] == "nwchess"


def test_missing_tournament_id_raises():
    with pytest.raises(ValueError):
        nwchess._extract_tournament_id("https://nwchess.com/OnlineRegistration/roster.php")
