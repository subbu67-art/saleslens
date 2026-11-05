# SalesLens — Sales Data Analysis System

Flask + Pandas + NumPy + Chart.js sales dashboard.

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Render deployment
Build: `pip install -r requirements.txt`
Start: `gunicorn app:app`

Set these Render environment variables:
- `SESSION_SECRET`: a long random secret
- `ADMIN_PASSWORD`: a strong admin password
- `SALES_DATA_DIR`: `/var/data` when a persistent disk is mounted at `/var/data`

For a free Render instance, the app stores uploads under the project data folder; this storage is ephemeral, so uploaded data may be lost after restart/redeploy. For durable uploads, attach a paid Render persistent disk mounted at `/var/data` and set `SALES_DATA_DIR=/var/data`. Public visitors can view dashboard, insights and sales. Upload and reset require admin login.

## CSV format
Required columns: `date,product,category,region,quantity,price`
Dates should be parseable; quantity must be positive; price must be zero or greater.
