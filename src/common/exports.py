"""Export utilities for tournament data."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List
from urllib.parse import parse_qs, urlparse

from src.agents.crawlers.nwchess import RosterEntry


def export_to_csv(entries: List[RosterEntry], output_path: Path) -> None:
    """Export roster entries to CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)

        # Write header
        writer.writerow([
            'Tournament ID',
            'Player Name',
            'Section',
            'USCF ID',
            'USCF Rating',
            'NWSRS ID',
            'NWSRS Rating'
        ])

        # Write data rows
        for entry in entries:
            writer.writerow([
                entry.source_tournament_id,
                entry.player_name,
                entry.session_name,
                entry.uscf_id or '',
                entry.uscf_rating or '',
                entry.nwsrs_id or '',
                entry.nwsrs_rating or ''
            ])


def export_to_html(entries: List[RosterEntry], output_path: Path, tournament_id: str) -> None:
    """Export roster entries to sortable HTML report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    html_content = _generate_html_report(entries, tournament_id)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


def _generate_html_report(entries: List[RosterEntry], tournament_id: str) -> str:
    """Generate HTML content with sortable table."""

    # Generate table rows
    table_rows = []
    for entry in entries:
        table_rows.append(f"""
        <tr>
            <td>{entry.player_name}</td>
            <td>{entry.session_name}</td>
            <td data-sort="{entry.uscf_rating or 0}">{entry.uscf_rating or '-'}</td>
            <td data-sort="{entry.nwsrs_rating or 0}">{entry.nwsrs_rating or '-'}</td>
            <td>{entry.uscf_id or '-'}</td>
            <td>{entry.nwsrs_id or '-'}</td>
        </tr>""")

    rows_html = ''.join(table_rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tournament {tournament_id} Roster</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
            cursor: pointer;
            user-select: none;
            position: relative;
        }}
        th:hover {{
            background-color: #45a049;
        }}
        th.sorted-asc::after {{
            content: " ↑";
            position: absolute;
            right: 8px;
        }}
        th.sorted-desc::after {{
            content: " ↓";
            position: absolute;
            right: 8px;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        tr:hover {{
            background-color: #e8f5e8;
        }}
        .stats {{
            background-color: #f0f0f0;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Tournament {tournament_id} Roster</h1>

        <div class="stats">
            <strong>Total Players:</strong> {len(entries)} |
            <strong>Generated:</strong> <span id="timestamp"></span>
        </div>

        <table id="rosterTable">
            <thead>
                <tr>
                    <th onclick="sortTable(0)">Player Name</th>
                    <th onclick="sortTable(1)">Section</th>
                    <th onclick="sortTable(2)">USCF Rating</th>
                    <th onclick="sortTable(3)">NWSRS Rating</th>
                    <th onclick="sortTable(4)">USCF ID</th>
                    <th onclick="sortTable(5)">NWSRS ID</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>

    <script>
        // Set current timestamp
        document.getElementById('timestamp').textContent = new Date().toLocaleString();

        let sortDirection = {{}};

        function sortTable(columnIndex) {{
            const table = document.getElementById('rosterTable');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const headers = table.querySelectorAll('th');

            // Clear previous sort indicators
            headers.forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));

            // Determine sort direction
            const currentDirection = sortDirection[columnIndex] || 'asc';
            const newDirection = currentDirection === 'asc' ? 'desc' : 'asc';
            sortDirection[columnIndex] = newDirection;

            // Add sort indicator
            headers[columnIndex].classList.add(`sorted-${{newDirection}}`);

            // Sort rows
            rows.sort((a, b) => {{
                let aVal = a.cells[columnIndex].textContent.trim();
                let bVal = b.cells[columnIndex].textContent.trim();

                // Handle numeric columns (ratings)
                if (columnIndex === 2 || columnIndex === 3) {{
                    const aSort = a.cells[columnIndex].getAttribute('data-sort');
                    const bSort = b.cells[columnIndex].getAttribute('data-sort');
                    aVal = parseInt(aSort) || 0;
                    bVal = parseInt(bSort) || 0;
                }} else {{
                    // Handle text columns
                    aVal = aVal.toLowerCase();
                    bVal = bVal.toLowerCase();
                }}

                let comparison = 0;
                if (aVal > bVal) comparison = 1;
                if (aVal < bVal) comparison = -1;

                return newDirection === 'desc' ? -comparison : comparison;
            }});

            // Re-append sorted rows
            rows.forEach(row => tbody.appendChild(row));
        }}

        // Default sort by player name
        sortTable(0);
    </script>
</body>
</html>"""


def get_tournament_filename(url: str, tournament_id: str) -> str:
    """Generate a filename for tournament exports."""
    return f"tournament_{tournament_id}"