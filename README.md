# homeshoppingcrawling

This project now includes a small Flask-based dashboard for exploring
home shopping broadcast schedules stored in a SQLite database.

## Dashboard

`dashboard.py` starts a web server that queries the `schedules` table in
`schedules.db` and renders the results as an HTML table at the
`/dashboard` route. The endpoint accepts optional query parameters to
filter the output:

- `category` – product category to show
- `channel` – broadcasting channel
- `date` – broadcast date in `YYYY-MM-DD` format

### Run

Install the required dependency and start the server:

```bash
pip install flask
python dashboard.py
```

Open [http://localhost:5000/dashboard](http://localhost:5000/dashboard)
in a browser and append the desired query parameters, for example:

```
http://localhost:5000/dashboard?category=electronics&channel=HSTV&date=2023-09-01
```

The application expects a SQLite database file named `schedules.db` with
a `schedules` table in the project root.
