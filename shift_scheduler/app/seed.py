from __future__ import annotations

from datetime import time

from .db import Base, engine, SessionLocal
from .models import Employee, ShiftTemplate


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Employee).count() == 0:
            db.add_all(
                [
                    Employee(name="Alice", role="Cashier"),
                    Employee(name="Bob", role="Barista"),
                    Employee(name="Charlie", role="Cook"),
                ]
            )
        if db.query(ShiftTemplate).count() == 0:
            db.add_all(
                [
                    ShiftTemplate(name="Morning", start_time=time(8, 0), end_time=time(16, 0)),
                    ShiftTemplate(name="Evening", start_time=time(16, 0), end_time=time(23, 0)),
                    ShiftTemplate(name="Midday", start_time=time(12, 0), end_time=time(20, 0)),
                ]
            )
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()