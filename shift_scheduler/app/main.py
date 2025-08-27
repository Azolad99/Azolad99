from __future__ import annotations

from datetime import date, timedelta, time
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Employee, ShiftAssignment, ShiftTemplate
from .routers.api import router as api_router
from .services.distributor import distribute_shifts_for_range

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Shift Scheduler")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# CORS for API usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    # Optional week start override: ?start=YYYY-MM-DD
    start_param = request.query_params.get("start")
    if start_param:
        try:
            today = date.fromisoformat(start_param)
        except ValueError:
            today = date.today()
    else:
        today = date.today()

    start = today - timedelta(days=today.weekday())
    days = [start + timedelta(days=i) for i in range(7)]

    employees = db.query(Employee).order_by(Employee.name.asc()).all()
    templates_ = db.query(ShiftTemplate).order_by(ShiftTemplate.name.asc()).all()

    # Prefetch assignments for the week
    assignments = (
        db.query(ShiftAssignment)
        .filter(ShiftAssignment.date.between(days[0], days[-1]))
        .all()
    )
    assignments_by_key = {(a.employee_id, a.date): a for a in assignments}

    prev_week = (start - timedelta(days=7)).isoformat()
    next_week = (start + timedelta(days=7)).isoformat()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "employees": employees,
            "templates": templates_,
            "days": days,
            "assignments_by_key": assignments_by_key,
            "start": start,
            "prev_week": prev_week,
            "next_week": next_week,
        },
    )


@app.post("/employees")
def create_employee(
    name: str = Form(...), role: str | None = Form(None), active: bool = Form(True), db: Session = Depends(get_db)
):
    employee = Employee(name=name.strip(), role=(role or None), active=1 if active else 0)
    db.add(employee)
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.post("/shift-templates")
def create_shift_template(
    name: str = Form(...), start_time: str = Form(...), end_time: str = Form(...), db: Session = Depends(get_db)
):
    try:
        start_h, start_m = map(int, start_time.split(":"))
        end_h, end_m = map(int, end_time.split(":"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid time format; expected HH:MM")

    st = ShiftTemplate(name=name.strip(), start_time=time(start_h, start_m), end_time=time(end_h, end_m))
    db.add(st)
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.post("/assign")
def assign_shift(
    employee_id: int = Form(...), date_str: str = Form(...), template_id: int | None = Form(None), db: Session = Depends(get_db)
):
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")

    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    existing = (
        db.query(ShiftAssignment)
        .filter(ShiftAssignment.employee_id == employee_id, ShiftAssignment.date == d)
        .one_or_none()
    )

    if template_id is None or template_id == 0:
        # Unassign
        if existing:
            db.delete(existing)
            db.commit()
    else:
        template = db.get(ShiftTemplate, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Shift template not found")
        if existing:
            existing.shift_template_id = template_id
        else:
            db.add(ShiftAssignment(employee_id=employee_id, date=d, shift_template_id=template_id))
        db.commit()

    return RedirectResponse(url="/", status_code=303)


@app.post("/distribute-week")
def distribute_week(request: Request, db: Session = Depends(get_db)):
    # Determine current week range shown on the grid
    start_param = request.query_params.get("start")
    if start_param:
        try:
            today = date.fromisoformat(start_param)
        except ValueError:
            today = date.today()
    else:
        today = date.today()

    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)

    distribute_shifts_for_range(db=db, start=start, end=end)
    return RedirectResponse(url=f"/?start={start.isoformat()}", status_code=303)


@app.post("/employees/{employee_id}/toggle")
def toggle_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    emp.active = 0 if emp.active else 1
    db.commit()
    return RedirectResponse(url="/", status_code=303)