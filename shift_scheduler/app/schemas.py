from __future__ import annotations

from datetime import date, time
from pydantic import BaseModel, Field


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    role: str | None = None
    active: bool = True


class EmployeeOut(BaseModel):
    id: int
    name: str
    role: str | None
    active: bool

    class Config:
        from_attributes = True


class ShiftTemplateCreate(BaseModel):
    name: str
    start_time: time
    end_time: time


class ShiftTemplateOut(BaseModel):
    id: int
    name: str
    start_time: time
    end_time: time

    class Config:
        from_attributes = True


class AssignmentCreate(BaseModel):
    employee_id: int
    date: date
    shift_template_id: int | None


class AssignmentOut(BaseModel):
    id: int
    date: date
    employee_id: int
    shift_template_id: int | None

    class Config:
        from_attributes = True