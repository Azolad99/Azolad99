from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Employee, ShiftTemplate, ShiftAssignment
from ..schemas import (
    EmployeeCreate,
    EmployeeOut,
    ShiftTemplateCreate,
    ShiftTemplateOut,
    AssignmentCreate,
    AssignmentOut,
)
from ..schemas import DistributeRequest, DistributeResponse
from ..services.distributor import distribute_shifts_for_range

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Employees
@router.get("/employees", response_model=List[EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    return db.query(Employee).order_by(Employee.name.asc()).all()


@router.post("/employees", response_model=EmployeeOut, status_code=201)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    employee = Employee(name=payload.name.strip(), role=payload.role, active=1 if payload.active else 0)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.get("/employees/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.patch("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(employee_id: int, payload: EmployeeCreate, db: Session = Depends(get_db)):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    employee.name = payload.name.strip()
    employee.role = payload.role
    employee.active = 1 if payload.active else 0
    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/employees/{employee_id}", status_code=204)
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.delete(employee)
    db.commit()
    return Response(status_code=204)


# Shift Templates
@router.get("/shift-templates", response_model=List[ShiftTemplateOut])
def list_templates(db: Session = Depends(get_db)):
    return db.query(ShiftTemplate).order_by(ShiftTemplate.name.asc()).all()


@router.post("/shift-templates", response_model=ShiftTemplateOut, status_code=201)
def create_template(payload: ShiftTemplateCreate, db: Session = Depends(get_db)):
    template = ShiftTemplate(name=payload.name.strip(), start_time=payload.start_time, end_time=payload.end_time)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/shift-templates/{template_id}", status_code=204)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    template = db.get(ShiftTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Shift template not found")
    db.delete(template)
    db.commit()
    return Response(status_code=204)


# Assignments
@router.get("/assignments", response_model=List[AssignmentOut])
def list_assignments(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(ShiftAssignment)
    if start and end:
        q = q.filter(ShiftAssignment.date.between(start, end))
    if employee_id:
        q = q.filter(ShiftAssignment.employee_id == employee_id)
    return q.all()


@router.post("/assignments", response_model=AssignmentOut, status_code=201)
def upsert_assignment(payload: AssignmentCreate, db: Session = Depends(get_db)):
    employee = db.get(Employee, payload.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if payload.shift_template_id is not None:
        template = db.get(ShiftTemplate, payload.shift_template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Shift template not found")

    existing = (
        db.query(ShiftAssignment)
        .filter(ShiftAssignment.employee_id == payload.employee_id, ShiftAssignment.date == payload.date)
        .one_or_none()
    )

    if payload.shift_template_id is None:
        if existing:
            db.delete(existing)
            db.commit()
            # Return 204 for unassign
            return Response(status_code=204)
        else:
            # No-op, but align with idempotent unassign
            return Response(status_code=204)

    if existing:
        existing.shift_template_id = payload.shift_template_id
        db.commit()
        db.refresh(existing)
        return existing

    assignment = ShiftAssignment(
        employee_id=payload.employee_id,
        date=payload.date,
        shift_template_id=payload.shift_template_id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment(assignment_id: int, db: Session = Depends(get_db)):
    assignment = db.get(ShiftAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(assignment)
    db.commit()
    return Response(status_code=204)


# Distribution
@router.post("/distribute", response_model=DistributeResponse)
def distribute(payload: DistributeRequest, db: Session = Depends(get_db)):
    if payload.start > payload.end:
        raise HTTPException(status_code=400, detail="start must be <= end")
    result = distribute_shifts_for_range(
        db=db,
        start=payload.start,
        end=payload.end,
        template_ids=payload.template_ids,
        employee_ids=payload.employee_ids,
        clear_existing=payload.clear_existing,
    )
    return result