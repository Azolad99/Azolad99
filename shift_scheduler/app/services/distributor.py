from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, Sequence

from sqlalchemy.orm import Session

from ..models import Employee, ShiftAssignment, ShiftTemplate


def _daterange(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current = current + timedelta(days=1)


def _round_robin_index(day_index: int, employee_index: int, num_templates: int) -> int:
    # Stagger by day and employee to avoid repetitive patterns
    return (day_index + employee_index) % num_templates


def distribute_shifts_for_range(
    db: Session,
    start: date,
    end: date,
    template_ids: Sequence[int] | None = None,
    employee_ids: Sequence[int] | None = None,
    clear_existing: bool = False,
):
    # Employees
    emp_query = db.query(Employee)
    if employee_ids:
        emp_query = emp_query.filter(Employee.id.in_(list(employee_ids)))
    else:
        emp_query = emp_query.filter(Employee.active == 1)
    employees: list[Employee] = emp_query.order_by(Employee.name.asc()).all()

    # Templates
    tpl_query = db.query(ShiftTemplate)
    if template_ids:
        tpl_query = tpl_query.filter(ShiftTemplate.id.in_(list(template_ids)))
    templates: list[ShiftTemplate] = tpl_query.order_by(ShiftTemplate.name.asc()).all()

    total_days = (end - start).days + 1
    skipped_days_without_templates = 0
    cleared = 0
    created = 0
    updated = 0

    if clear_existing:
        del_q = db.query(ShiftAssignment).filter(ShiftAssignment.date.between(start, end))
        if employee_ids:
            del_q = del_q.filter(ShiftAssignment.employee_id.in_(list(employee_ids)))
        cleared = del_q.count()
        # Use bulk delete for efficiency
        del_q.delete(synchronize_session=False)
        db.flush()

    if not templates:
        # Nothing to assign; all days skipped
        skipped_days_without_templates = total_days
        db.commit()
        return {
            "created": created,
            "updated": updated,
            "cleared": cleared,
            "skipped_days_without_templates": skipped_days_without_templates,
            "total_days": total_days,
        }

    # Map for quick existing lookup if not clearing
    existing_by_key: dict[tuple[int, date], ShiftAssignment] = {}
    if not clear_existing:
        existing = (
            db.query(ShiftAssignment)
            .filter(ShiftAssignment.date.between(start, end))
            .all()
        )
        existing_by_key = {(a.employee_id, a.date): a for a in existing}

    days = list(_daterange(start, end))
    for day_index, d in enumerate(days):
        if not employees:
            break
        for employee_index, emp in enumerate(employees):
            tpl_idx = _round_robin_index(day_index, employee_index, len(templates))
            tpl_id = templates[tpl_idx].id

            key = (emp.id, d)
            found = existing_by_key.get(key)
            if found is None:
                # Create new
                db.add(ShiftAssignment(employee_id=emp.id, date=d, shift_template_id=tpl_id))
                created += 1
            else:
                if found.shift_template_id != tpl_id:
                    found.shift_template_id = tpl_id
                    updated += 1

    db.commit()
    return {
        "created": created,
        "updated": updated,
        "cleared": cleared,
        "skipped_days_without_templates": skipped_days_without_templates,
        "total_days": total_days,
    }

