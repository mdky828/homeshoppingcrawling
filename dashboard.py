from flask import Flask, request, render_template_string
import sqlite3
from pathlib import Path
from typing import List, Optional

app = Flask(__name__)

DATABASE_PATH = Path(__file__).parent / 'schedules.db'


def get_schedules(
    category: Optional[str] = None,
    channel: Optional[str] = None,
    date: Optional[str] = None,
):
    """Query schedules from SQLite DB with optional filters."""
    if not DATABASE_PATH.exists():
        return []
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    query = 'SELECT * FROM schedules WHERE 1=1'
    params: List[str] = []
    if category:
        query += ' AND category = ?'
        params.append(category)
    if channel:
        query += ' AND channel = ?'
        params.append(channel)
    if date:
        query += ' AND date = ?'
        params.append(date)
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


@app.route('/dashboard')
def dashboard():
    category = request.args.get('category')
    channel = request.args.get('channel')
    date = request.args.get('date')
    rows = get_schedules(category, channel, date)
    columns = rows[0].keys() if rows else []
    html = render_template_string(
        """
        <html>
        <head><title>Broadcast Dashboard</title></head>
        <body>
            <h1>Broadcast Schedule</h1>
            {% if rows %}
            <table border="1" cellspacing="0" cellpadding="4">
                <tr>
                    {% for col in columns %}<th>{{ col }}</th>{% endfor %}
                </tr>
                {% for row in rows %}
                <tr>
                    {% for col in columns %}<td>{{ row[col] }}</td>{% endfor %}
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No data found.</p>
            {% endif %}
        </body>
        </html>
        """,
        rows=rows,
        columns=columns,
    )
    return html


if __name__ == '__main__':
    app.run(debug=True)
