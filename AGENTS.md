# Repository Guidelines

## Project Structure & Module Organization
Organize all runtime code under `src/`, using feature-specific packages such as `src/engine/` for core chess logic and `src/agents/` for strategy or platform adapters. Keep user-facing interfaces in `src/interface/` (CLI, API hooks) and reusable utilities in `src/common/`. Place PGN samples, evaluation tables, or prompt templates in `resources/`. Mirror the runtime tree inside `tests/`, and add design notes or protocol descriptions to `docs/` so new contributors can ramp up quickly.

## Build, Test, and Development Commands
Create a virtual environment with `python3 -m venv .venv` and activate it via `source .venv/bin/activate`. Install dependencies once `requirements.txt` or `pyproject.toml` is introduced by running `pip install -r requirements.txt`. Use `pytest` from the repo root to execute the full suite; scope to a module with `pytest tests/agents/test_opening_book.py` when iterating. Run `python -m src.interface.cli` to exercise the assistant end-to-end. Add a simple `make test` wrapper once automation lands so CI mirrors local steps.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation and prefer type hints on all public functions. Name modules and files with `snake_case`, classes with `PascalCase`, and constants with `UPPER_CASE`. Keep chess-specific helpers descriptive (e.g., `serialize_fen`, `score_mobility`). Document complex heuristics with short docstrings, and rely on `black` + `ruff` for formatting and linting when the toolchain is added.

## Testing Guidelines
Use `pytest` fixtures to set up boards or mock engines, and snapshot tricky move sequences under `tests/fixtures/`. Each test module should mirror its source module and use names like `test_move_generator_rejects_illegal_castle`. Target >90% statement coverage for the engine while allowing lower coverage for experiment sandboxes. When adding new agents, include regression tests covering both best-move selection and failure-handling paths.

## Commit & Pull Request Guidelines
Write commits in the imperative mood (`Add quiescence search guard`) and keep them focused on one change-set. Reference issue IDs in the subject or footer when applicable. Pull requests should summarize intent, list testing performed, and attach PGN diffs or CLI transcripts that show the new behaviour. Request review from a second agent before merging anything that impacts move generation or time controls.
