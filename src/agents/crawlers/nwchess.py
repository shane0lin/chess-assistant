"""Crawler for NWChess tournament rosters."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
from typing import Iterable, List, Optional
from urllib.parse import parse_qs, urlparse
import uuid

import requests
from bs4 import BeautifulSoup

from src.common import db as db_module


_SOURCE = "nwchess"
_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://nwchess.com/OnlineRegistration/")


@dataclass(frozen=True)
class RosterEntry:
    universal_tournament_id: str
    universal_player_id: str
    player_name: str
    session_name: str
    uscf_id: Optional[str]
    uscf_rating: Optional[int]
    source_tournament_id: str


class NwChessRosterCrawler:
    """Fetch and persist roster data for NWChess tournaments."""

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self._session = session or requests.Session()

    def crawl(
        self, url: str, connection: Optional[sqlite3.Connection] = None
    ) -> List[RosterEntry]:
        html = self._fetch(url)
        source_tournament_id = self._extract_tournament_id(url)
        universal_tournament_id = _build_tournament_uuid(source_tournament_id)
        entries = list(
            _parse_entries(
                html=html,
                source_tournament_id=source_tournament_id,
                universal_tournament_id=universal_tournament_id,
            )
        )

        db_conn = connection or db_module.ensure_database()
        try:
            _persist_entries(db_conn, entries)
        finally:
            if connection is None:
                db_conn.close()
        return entries

    def _fetch(self, url: str) -> str:
        response = self._session.get(url, timeout=30)
        response.raise_for_status()
        response.encoding = response.encoding or "utf-8"
        return response.text

    @staticmethod
    def _extract_tournament_id(url: str) -> str:
        return _extract_tournament_id(url)


def _extract_tournament_id(url: str) -> str:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    tournament_ids = params.get("tournamentid")
    if not tournament_ids or not tournament_ids[0].strip():
        raise ValueError("NWChess roster URL must include a tournamentid query parameter")
    return tournament_ids[0].strip()


def _build_tournament_uuid(source_tournament_id: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, f"tournament:{source_tournament_id}"))


def _build_player_uuid(universal_tournament_id: str, player_name: str, uscf_id: Optional[str]) -> str:
    namespace = uuid.UUID(universal_tournament_id)
    canonical_id = uscf_id.strip() if uscf_id else player_name.lower()
    return str(uuid.uuid5(namespace, canonical_id))


def _parse_entries(
    *,
    html: str,
    source_tournament_id: str,
    universal_tournament_id: str,
) -> Iterable[RosterEntry]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "RosterTable"})
    if table is None:
        raise ValueError("Roster table not found in NWChess response")

    for row in table.find_all("tr"):
        cells = [cell.get_text(strip=True) for cell in row.find_all("td")]
        if not cells or len(cells) < 9:
            continue
        if cells[0] in {"", "Section"}:
            continue
        if cells[1] in {"Name", "Last"}:
            continue

        session_name = cells[0]
        last_name = cells[1]
        first_name = cells[2]
        player_name = _compose_player_name(first_name, last_name)
        uscf_rating = _parse_int(cells[7])
        uscf_id = cells[8] or None

        universal_player_id = _build_player_uuid(
            universal_tournament_id, player_name, uscf_id
        )

        yield RosterEntry(
            universal_tournament_id=universal_tournament_id,
            universal_player_id=universal_player_id,
            player_name=player_name,
            session_name=session_name,
            uscf_id=uscf_id,
            uscf_rating=uscf_rating,
            source_tournament_id=source_tournament_id,
        )


def _compose_player_name(first_name: str, last_name: str) -> str:
    return " ".join(part for part in [first_name.strip(), last_name.strip()] if part)


def _parse_int(value: str) -> Optional[int]:
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:  # pragma: no cover - defensive path
        raise ValueError(f"Unable to parse integer from value '{value}'") from exc


def _persist_entries(connection, entries: Iterable[RosterEntry]) -> None:
    now = datetime.now(tz=timezone.utc).isoformat()
    with connection:
        for entry in entries:
            connection.execute(
                """
                INSERT INTO tournament_players (
                    universal_tournament_id,
                    universal_player_id,
                    source,
                    source_tournament_id,
                    player_name,
                    session_name,
                    uscf_id,
                    uscf_rating,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(universal_tournament_id, universal_player_id)
                DO UPDATE SET
                    player_name=excluded.player_name,
                    session_name=excluded.session_name,
                    uscf_id=excluded.uscf_id,
                    uscf_rating=excluded.uscf_rating,
                    source=excluded.source,
                    source_tournament_id=excluded.source_tournament_id,
                    updated_at=excluded.updated_at
                """,
                (
                    entry.universal_tournament_id,
                    entry.universal_player_id,
                    _SOURCE,
                    entry.source_tournament_id,
                    entry.player_name,
                    entry.session_name,
                    entry.uscf_id,
                    entry.uscf_rating,
                    now,
                    now,
                ),
            )
