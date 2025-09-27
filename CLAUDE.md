# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Setup

This is a Python project using a virtual environment setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the Application

The main entry point is `main.py` which provides a command-line interface for crawling NWChess tournament rosters:

```bash
# Crawl a tournament roster and save to default database
python main.py "https://nwchess.com/OnlineRegistration/roster.php?tournamentid=977"

# Specify a custom database path
python main.py --db-path path/to/custom.db "https://nwchess.com/OnlineRegistration/roster.php?tournamentid=977"
```

## Testing

Run tests using pytest:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/agents/crawlers/test_nwchess.py

# Install pytest if not available
pip install pytest
```

## Architecture Overview

This is a chess tournament data management system with the following key components:

### Core Structure
- `src/agents/crawlers/` - Web crawlers for tournament data sources
- `src/common/db.py` - SQLite database utilities and schema management
- `main.py` - CLI entry point for crawling operations

### Database Schema
The system uses SQLite with a `tournament_players` table that stores:
- Universal tournament/player IDs (UUIDs derived from source data)
- Player information (name, USCF ID, rating, session)
- Source tracking and timestamps
- Composite primary key prevents duplicates

### Data Flow
1. **Crawling**: `NwChessRosterCrawler` fetches HTML from NWChess roster URLs
2. **Parsing**: Extracts player data from HTML tables using BeautifulSoup
3. **Normalization**: Generates universal IDs using UUID5 for consistent player/tournament identification
4. **Persistence**: Upserts data to SQLite using conflict resolution

### Key Design Patterns
- Universal ID system allows merging data from multiple sources
- Crawler abstraction supports adding new tournament data sources
- Database connection management with automatic schema initialization
- Default database location: `resources/chessassistant.db`

## Dependencies
- `beautifulsoup4` - HTML parsing for web scraping
- `requests` - HTTP client for fetching tournament pages
- `pytest` - Testing framework