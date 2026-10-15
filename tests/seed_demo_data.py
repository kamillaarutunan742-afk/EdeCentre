"""Наполнение базы тестовыми данными языковой школы."""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db import SessionLocal, init_db
from database.models import Attendance, Notification, Payment
from services.auth_service import register_user
from services.group_service import GroupService
from services.schedule_service import ScheduleService
from services.student_service import StudentService
from services.subscription_service import SubscriptionService
from services.teacher_service import TeacherService


def seed() -> None:
    """Создаёт пользователей и демо-данные школы."""
    init_db()
    session = SessionLocal()

    print("Шаг 1/7: пользователи…")
    register_user("admin", "admin", role="admin", full_name="Администратор")
    register_user(
        "manager", "manager", role="manager", full_name="Менеджер Иванова И. И."
    )

    print("Шаг 2/7: преподаватели…")
    teachers = TeacherService(session)
    t1 = teachers.create_teacher(
        "Ковалёва М. А.", phone="+7 913 111-22-33", subjects="Английский"
    )
    t2 = teachers.create_teacher(
        "Шмидт И. П.", phone="+7 913 222-33-44", subjects="Немецкий"
    )
    t3 = teachers.create_teacher(
        "Диоп А. К.", phone="+7 913 333-44-55", subjects="Французский, Испанский"
    )

    print("Шаг 3/7: группы…")
    groups = GroupService(session)
    g1 = groups.create_group(
        "Английский A1", "Английский", "7-10", "beginner", 12, teacher_id=t1.teacher_id
    )
    g2 = groups.create_group(
        "Английский B2", "Английский", "15-17", "advanced", 10, teacher_id=t1.teacher_id
    )
    g3 = groups.create_group(
        "Немецкий A2", "Немецкий", "11-14", "elementary", 12, teacher_id=t2.teacher_id
    )
    g4 = groups.create_group(
        "Немецкий B1", "Немецкий", "18+", "intermediate", 10, teacher_id=t2.teacher_id
    )
    g5 = groups.create_group(
        "Французский A1", "Французский", "18+", "beginner", 12, teacher_id=t3.teacher_id
    )
    g6 = groups.create_group(
        "Испанский A2", "Испанский", "18+", "elementary", 12, teacher_id=t3.teacher_id
    )

    print("Шаг 4/7: ученики…")
    students = StudentService(session)
    names = (
        "Иванов Иван Алексеевич",
        "Петров Пётр Сергеевич",
        "Сидорова Анна Михайловна",
        "Козлов Дмитрий Олегович",
        "Смирнова Екатерина Игоревна",
        "Морозов Алексей Владимирович",
        "Новикова Ольга Павловна",
        "Фёдоров Сергей Андреевич",
    )
    created = [
        students.create_student(
            name,
            phone=f"+7 900 234-56-{i:02d}",
            direction="Английский" if i % 2 else "Немецкий",
            level="beginner",
            parent_name=f"Родитель {i}",
        )
        for i, name in enumerate(names, start=1)
    ]
    student_groups = (g1, g3, g3, g2, g6, g1, g4, g2)
    for group, student in zip(student_groups, created):
        groups.add_student(group, student.student_id)

    print("Шаг 5/7: абонементы и оплаты…")
    subs = SubscriptionService(session)
    type_8 = subs.create_type("8 занятий", 8, 8000)
    type_12 = subs.create_type("12 занятий", 12, 12000)
    type_4 = subs.create_type("4 занятия", 4, 4000)
    type_16 = subs.create_type("16 занятий", 16, 16000)
    type_map = (type_8, type_12, type_4, type_16, type_8, type_12, type_8, type_4)
    remaining = (5, 3, 2, 10, 8, 4, 1, 2)
    for student, sub_type, left in zip(created, type_map, remaining):
        subscription = subs.sell_subscription(student.student_id, sub_type.type_id)
        subscription.remaining_lessons = left
        session.commit()

    pay_map = (8000, 10000, 4000, 12500, 8000, 10500, 8000, 2000)
    methods = (
        "Безналичный",
        "Наличный",
        "Безналичный",
        "Безналичный",
        "Наличный",
        "Наличный",
        "Безналичный",
        "Безналичный",
    )
    for student, amount, method in zip(created, pay_map, methods):
        session.add(
            Payment(
                student_id=student.student_id,
                amount=float(amount),
                payment_date=date.today() - timedelta(days=3),
                method=method,
            )
        )
    session.commit()

    print("Шаг 6/7: посещаемость…")
    statuses = (
        "present",
        "absent",
        "sick",
        "present",
        "present",
        "present",
        "present",
        "absent",
    )
    for offset in range(4):
        lesson_date = date.today() - timedelta(days=offset + 1)
        for index, student in enumerate(created):
            status = statuses[(index + offset) % len(statuses)]
            session.add(
                Attendance(
                    student_id=student.student_id,
                    group_id=student_groups[index].group_id,
                    lesson_date=lesson_date,
                    status=status,
                )
            )
    session.commit()

    print("Шаг 7/7: занятия расписания и уведомления…")
    schedule = ScheduleService(session)
    lessons = (
        (g1, "Понедельник", "16:00", "17:00", "201"),
        (g1, "Среда", "16:00", "17:00", "201"),
        (g2, "Вторник", "18:00", "19:30", "202"),
        (g2, "Четверг", "18:00", "19:30", "202"),
        (g3, "Понедельник", "15:00", "16:00", "203"),
        (g4, "Пятница", "18:30", "19:30", "203"),
        (g5, "Суббота", "11:00", "12:00", "204"),
        (g6, "Вторник", "19:00", "20:00", "205"),
    )
    for group, day, start, end, room in lessons:
        try:
            schedule.create_lesson(group.group_id, day, start, end=end, room=room)
        except ValueError:
            pass
    session.commit()

    now = datetime.now()
    notes = [
        (
            "Абонемент «8 занятий» Новиковой О. заканчивается (осталось 1 занятие)",
            "subscription",
            2,
            False,
        ),
        (
            "Абонемент «4 занятия» Сидоровой А. заканчивается (осталось 2 занятия)",
            "subscription",
            15,
            False,
        ),
        ("Петров П. имеет задолженность 2000 руб.", "payment", 60, False),
        ("Козлов Д. имеет задолженность 3500 руб.", "payment", 120, True),
        (
            "Абонемент «12 занятий» Морозова А. истекает 15.10.2026",
            "expiry",
            1440,
            True,
        ),
        (
            "Абонемент «8 занятий» Иванова И. — осталось 5 занятий",
            "subscription",
            1500,
            True,
        ),
        ("Морозов А. имеет задолженность 1500 руб.", "payment", 2880, True),
        ("Абонемент «4 занятия» Фёдорова С. истекает 20.10.2026", "expiry", 4320, True),
    ]
    for message, note_type, minutes_ago, is_read in notes:
        session.add(
            Notification(
                message=message,
                type=note_type,
                is_read=is_read,
                created_at=now - timedelta(minutes=minutes_ago),
            )
        )
    session.commit()
    session.close()
    print("Демо-данные созданы: admin/admin, manager/manager")


if __name__ == "__main__":
    try:
        seed()
    except Exception:
        import traceback

        traceback.print_exc()
        print("СИД УПАЛ — база может быть заполнена не полностью")
        raise
