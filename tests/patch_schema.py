"""Добавляет недостающие колонки age_range, room, end_time в базу."""

import sys
from pathlib import Path

from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db import engine
from database.models import Group, Schedule

TABLES = {
    Group: (("age_range", "VARCHAR(20)"),),
    Schedule: (("room", "VARCHAR(50)"), ("end_time", "VARCHAR(5)")),
}


def main() -> None:
    """Проверяет колонки и добавляет недостающие через ALTER TABLE."""
    for model, columns in TABLES.items():
        table = model.__table__.name
        existing = [column["name"] for column in inspect(engine).get_columns(table)]
        print(f"{table}: колонки -> {existing}")
        for name, ddl in columns:
            if name in existing:
                print(f"  уже есть: {name}")
                continue
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
            print(f"  добавлено: {name}")


if __name__ == "__main__":
    main()
