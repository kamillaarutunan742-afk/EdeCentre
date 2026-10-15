"""Тесты сервисов: аутентификация, посещаемость, расписание."""

from datetime import date

import pytest

from database.models import (
    Attendance,
    Group,
    GroupStudent,
    Student,
    Subscription,
)

from services.attendance_service import AttendanceService
from services.schedule_service import ScheduleService


# ---------- Аутентификация ----------

def test_register_and_authenticate(auth_service_session):
    """Регистрация и вход с верным паролем."""
    user = auth_service_session.register_user(
        "anna", "secret1", role="student", full_name="Анна",
        secret_word="школа",
    )
    assert user is not None
    assert auth_service_session.authenticate("anna", "secret1") is not None


def test_authenticate_wrong_password(auth_service_session):
    """Вход с неверным паролем не проходит."""
    auth_service_session.register_user("anna", "secret1")
    assert auth_service_session.authenticate("anna", "wrong!") is None


def test_register_duplicate_login(auth_service_session):
    """Повторный логин не регистрируется."""
    auth_service_session.register_user("anna", "secret1")
    assert auth_service_session.register_user("anna", "other1") is None


def test_register_short_password(auth_service_session):
    """Пароль короче 6 символов отклоняется."""
    assert auth_service_session.register_user("boris", "123") is None


def test_change_password_requires_old(auth_service_session):
    """Смена пароля без верного текущего не проходит."""
    auth_service_session.register_user("anna", "secret1")
    ok, _ = auth_service_session.change_password("anna", "bad_old", "newpass1")
    assert ok is False
    ok, _ = auth_service_session.change_password("anna", "secret1", "newpass1")
    assert ok is True
    assert auth_service_session.authenticate("anna", "newpass1") is not None


def test_reset_password_with_secret(auth_service_session):
    """Восстановление по секретному слову; без него — отказ."""
    auth_service_session.register_user("anna", "secret1", secret_word="школа")
    ok, _ = auth_service_session.reset_password_with_secret(
        "anna", "неверное", "newpass1"
    )
    assert ok is False
    ok, _ = auth_service_session.reset_password_with_secret(
        "anna", "ШКОЛА", "newpass1"
    )
    assert ok is True
    assert auth_service_session.authenticate("anna", "newpass1") is not None


def test_old_hash_not_reused(auth_service_session):
    """После смены пароля старый больше не работает."""
    auth_service_session.register_user("anna", "secret1")
    auth_service_session.change_password("anna", "secret1", "newpass1")
    assert auth_service_session.authenticate("anna", "secret1") is None


# ---------- Вспомогательное для посещаемости и расписания ----------

@pytest.fixture()
def group_with_students(session):
    """Группа с двумя учениками."""
    group = Group(name="Английский A1")
    session.add(group)
    session.flush()
    for name in ("Иванов Иван", "Петрова Мария"):
        student = Student(full_name=name)
        session.add(student)
        session.flush()
        session.add(GroupStudent(group_id=group.group_id,
                                 student_id=student.student_id))
    session.commit()
    return group


@pytest.fixture()
def subscription(session, group_with_students):
    """Активный абонемент первому ученику на 2 занятия."""
    sub = Subscription(
        student_id=1, type_id=1, total_lessons=2,
        remaining_lessons=2, status="active",
    )
    session.add(sub)
    session.commit()
    return sub


# ---------- Посещаемость ----------

def test_mark_lesson_creates_records(session, group_with_students, subscription):
    """Отметка создаёт по одной записи на каждого ученика."""
    service = AttendanceService(session)
    day = date(2026, 10, 14)
    service.mark_lesson(group_with_students, day, {1: "present", 2: "absent"})
    assert session.query(Attendance).filter_by(lesson_date=day).count() == 2


def test_mark_and_no_duplicates(session, group_with_students, subscription):
    """Повторная отметка за тот же день не создаёт дубликатов
    и не списывает занятие второй раз."""
    service = AttendanceService(session)
    day = date(2026, 10, 14)
    service.mark_lesson(group_with_students, day,
                        {1: "present", 2: "absent"})
    assert session.query(Subscription).filter_by(
        subscription_id=subscription.subscription_id
    ).first().remaining_lessons == 1
    service.mark_lesson(group_with_students, day,
                        {1: "present", 2: "absent"})
    rows = session.query(Attendance).filter_by(lesson_date=day).all()
    assert len(rows) == 2
    assert session.query(Subscription).filter_by(
        subscription_id=subscription.subscription_id
    ).first().remaining_lessons == 1


def test_set_status_refunds_lesson(session, group_with_students, subscription):
    """Смена «присутствовал» на «отсутствовал» возвращает занятие."""
    from database.models import Attendance

    service = AttendanceService(session)
    day = date(2026, 10, 14)
    service.mark_lesson(group_with_students, day,
                        {1: "present", 2: "absent"})
    record = session.query(Attendance).filter_by(
        student_id=1, lesson_date=day).one()
    service.set_status(record.attendance_id, "absent")
    assert session.query(Subscription).filter_by(
        subscription_id=subscription.subscription_id
    ).first().remaining_lessons == 2
    service.set_status(record.attendance_id, "present")
    assert session.query(Subscription).filter_by(
        subscription_id=subscription.subscription_id
    ).first().remaining_lessons == 1


def test_set_status_invalid(session, group_with_students):
    """Незвестный статус отклоняется."""
    service = AttendanceService(session)
    with pytest.raises(ValueError):
        service.set_status(999, "vacation")


# ---------- Расписание ----------

def test_create_lesson_requires_date(session, group_with_students):
    """Занятие без даты не создаётся."""
    service = ScheduleService(session)
    with pytest.raises(ValueError):
        service.create_lesson(group_with_students.group_id, None, "18:00")


def test_create_lesson_fills_weekday(session, group_with_students):
    """День недели вычисляется из даты автоматически."""
    service = ScheduleService(session)
    lesson = service.create_lesson(group_with_students.group_id,
                                   date(2026, 10, 14), "18:00",
                                   end="19:00")
    assert lesson.day_of_week == "Среда"


def test_create_lesson_conflict(session, group_with_students):
    """Пересекающееся занятие той же группы в тот же день отклоняется."""
    service = ScheduleService(session)
    day = date(2026, 10, 14)
    service.create_lesson(group_with_students.group_id, day, "18:00",
                          end="19:00")
    with pytest.raises(ValueError):
        service.create_lesson(group_with_students.group_id, day, "18:30",
                              end="19:30")


def test_create_lesson_no_conflict_other_time(session, group_with_students):
    """Занятия в разное время того же дня не конфликтуют."""
    service = ScheduleService(session)
    day = date(2026, 10, 14)
    service.create_lesson(group_with_students.group_id, day, "18:00",
                          end="19:00")
    lesson = service.create_lesson(group_with_students.group_id, day,
                                   "19:00", end="20:00")
    assert lesson.schedule_id is not None
