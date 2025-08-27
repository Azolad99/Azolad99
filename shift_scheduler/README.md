# Shift Scheduler

A minimal FastAPI + SQLite app to manage employees, shift templates, and weekly assignments with a simple web UI and a REST API.

## Features

- Employees: add/list/toggle via UI, full CRUD via API
- Shift templates: add/list via UI, CRUD via API
- Assign shifts on a weekly grid; assign/unassign via UI and API
- REST API under `/api` and health check at `/health` and `/api/health`

## Quickstart (local)

```bash
# Create venv (if not already created)
python3 -m venv .venv
. .venv/bin/activate

# Install deps
pip install --upgrade pip
pip install -r requirements.txt

# (Optional) seed sample data
python -m app.seed

# Run dev server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000` in your browser.

## API examples

```bash
# Health
curl http://localhost:8000/api/health

# Employees
curl http://localhost:8000/api/employees
curl -X POST http://localhost:8000/api/employees -H 'Content-Type: application/json' \
  -d '{"name":"Dana","role":"Supervisor","active":true}'

# Shift templates
curl http://localhost:8000/api/shift-templates
curl -X POST http://localhost:8000/api/shift-templates -H 'Content-Type: application/json' \
  -d '{"name":"Night","start_time":"22:00:00","end_time":"06:00:00"}'

# Assignments (upsert; pass null to unassign)
curl -X POST http://localhost:8000/api/assignments -H 'Content-Type: application/json' \
  -d '{"employee_id":1,"date":"2025-01-01","shift_template_id":1}'
  
# Auto-distribute shifts
# API
curl -X POST http://localhost:8000/api/distribute -H 'Content-Type: application/json' \
  -d '{"start":"2025-01-06","end":"2025-01-12","clear_existing":true}'

# UI
Use the "Auto-distribute week" button at the top of the schedule to fill the current week for all active employees with available shift templates.
```

## Docker

```bash
# Build
docker build -t shift-scheduler .

# Run
docker run --rm -p 8000:8000 -v $(pwd)/shift.db:/app/shift.db shift-scheduler
```

The SQLite database is stored at `shift.db`. Mount it as a volume to persist data.