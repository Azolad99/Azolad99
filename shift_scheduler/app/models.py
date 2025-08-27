from __future__ import annotations

from datetime import date, time
from sqlalchemy import Column, Date, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str | None] = mapped_column(String(200), nullable=True)
    active: Mapped[int] = mapped_column(Integer, default=1)  # 1=true, 0=false for SQLite simplicity

    assignments: Mapped[list[ShiftAssignment]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )


class ShiftTemplate(Base):
    __tablename__ = "shift_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    assignments: Mapped[list[ShiftAssignment]] = relationship(
        back_populates="shift_template", cascade="all, delete-orphan"
    )


class ShiftAssignment(Base):
    __tablename__ = "shift_assignments"
    __table_args__ = (UniqueConstraint("employee_id", "date", name="uq_assignment_emp_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)

    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    shift_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("shift_templates.id", ondelete="SET NULL"), nullable=True
    )

    employee: Mapped[Employee] = relationship(back_populates="assignments")
    shift_template: Mapped[ShiftTemplate | None] = relationship(back_populates="assignments")