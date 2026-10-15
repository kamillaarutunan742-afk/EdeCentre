"""Печатает колонки моделей Schedule, Group, Subscription."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.models import Group, Schedule, Subscription

for model in (Schedule, Group, Subscription):
    print(model.__name__, "->", [column.name for column in model.__table__.columns])
