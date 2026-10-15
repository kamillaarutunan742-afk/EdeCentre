"""Разовая миграция: secret_word у пользователей и lesson_date в расписании."""

import sqlite3

conn = sqlite3.connect("education_center.db")
for statement in (
    "ALTER TABLE users ADD COLUMN secret_word TEXT",
    "ALTER TABLE schedule ADD COLUMN lesson_date DATE",
):
    try:
        conn.execute(statement)
        conn.commit()
        print("готово:", statement)
    except sqlite3.OperationalError as error:
        print("пропущено:", error)
conn.close()
