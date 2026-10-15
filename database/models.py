"""Модели базы данных языковой школы EduCenter."""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """Пользователь системы."""

    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    login = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(64), nullable=False)
    role = Column(String(20), nullable=False, default="student")
    full_name = Column(String(120), default="")
    secret_word = Column(String(100), default="")  # слово для восстановления пароля


class Teacher(Base):
    """Преподаватель."""

    __tablename__ = "teachers"

    teacher_id = Column(Integer, primary_key=True)
    full_name = Column(String(120), nullable=False)
    phone = Column(String(20), default="")
    subjects = Column(String(200), default="")
    groups = relationship("Group", back_populates="teacher")


class Group(Base):
    """Учебная группа."""

    __tablename__ = "groups"

    group_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    direction = Column(String(50), default="")
    level = Column(String(20), default="")
    age_range = Column(String(20), default="")
    teacher_id = Column(Integer, ForeignKey("teachers.teacher_id"))
    teacher = relationship("Teacher", back_populates="groups")
    student_links = relationship(
        "GroupStudent",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    students = relationship(
        "Student",
        secondary="group_students",
        viewonly=True,
        back_populates="groups",
    )
    lessons = relationship(
        "Schedule",
        back_populates="group",
        cascade="all, delete-orphan",
    )


class GroupStudent(Base):
    """Связь ученика с группой."""

    __tablename__ = "group_students"

    link_id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.group_id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=False)
    group = relationship("Group", back_populates="student_links")
    student = relationship("Student", back_populates="group_links")


class Student(Base):
    """Ученик."""

    __tablename__ = "students"

    student_id = Column(Integer, primary_key=True)
    full_name = Column(String(120), nullable=False)
    phone = Column(String(20), default="")
    direction = Column(String(50), default="")
    level = Column(String(20), default="")
    parent_name = Column(String(120), default="")
    enroll_date = Column(Date, default=date.today)
    group_links = relationship(
        "GroupStudent",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    groups = relationship(
        "Group",
        secondary="group_students",
        viewonly=True,
        back_populates="students",
    )


class Schedule(Base):
    """Занятие в расписании: обязательная конкретная дата."""

    __tablename__ = "schedule"

    schedule_id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.group_id"), nullable=False)
    lesson_date = Column(Date, nullable=True)  # конкретная дата занятия
    day_of_week = Column(String(20), nullable=False, default="")
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), default="")
    room = Column(String(50), default="")
    group = relationship("Group", back_populates="lessons")


class SubscriptionType(Base):
    """Тип абонемента."""

    __tablename__ = "subscription_types"

    type_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    lessons_count = Column(Integer, nullable=False)
    price = Column(Float, nullable=False, default=0.0)


class Subscription(Base):
    """Абонемент ученика."""

    __tablename__ = "subscriptions"

    subscription_id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=False)
    type_id = Column(Integer, ForeignKey("subscription_types.type_id"), nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)
    total_lessons = Column(Integer, nullable=False, default=0)
    remaining_lessons = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="active")
    student = relationship("Student", backref="subscriptions")
    subscription_type = relationship("SubscriptionType")


class Attendance(Base):
    """Отметка посещаемости."""

    __tablename__ = "attendance"

    attendance_id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.group_id"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("schedule.schedule_id"))
    subscription_id = Column(Integer, ForeignKey("subscriptions.subscription_id"))
    lesson_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="present")


class Payment(Base):
    """Оплата."""

    __tablename__ = "payments"

    payment_id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(Date, nullable=False)
    method = Column(String(30), default="")


class Notification(Base):
    """Уведомление."""

    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True)
    message = Column(String(300), nullable=False)
    type = Column(String(30), default="info")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
