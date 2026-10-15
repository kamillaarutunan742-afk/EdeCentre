from __future__ import annotations
"""Сервис аутентификации: вход, регистрация, смена и восстановление пароля."""

import hashlib

from sqlalchemy import select

from database.db import SessionLocal
from database.models import User

MIN_PASSWORD_LEN = 6


def hash_password(password: str) -> str:
    """Хеширует пароль SHA-256.

    Args:
        password: пароль в открытом виде.

    Returns:
        Шестнадцатеричная строка хеша.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def authenticate(login: str, password: str) -> User | None:
    """Проверяет логин и пароль.

    Args:
        login: логин пользователя.
        password: пароль в открытом виде.

    Returns:
        Объект User при успехе, иначе None.
    """
    session = SessionLocal()
    try:
        user = session.scalar(select(User).where(User.login == login))
        if user is not None and user.password_hash == hash_password(password):
            session.refresh(user)
            return user
        return None
    finally:
        session.close()


def register_user(
    login: str,
    password: str,
    role: str = "student",
    full_name: str | None = None,
    secret_word: str = "",
) -> User | None:
    """Регистрирует нового пользователя.

    Args:
        login: логин.
        password: пароль.
        role: роль пользователя.
        full_name: полное имя (по умолчанию — логин).
        secret_word: слово для восстановления пароля.

    Returns:
        Созданный User или None, если логин занят или пароль короткий.
    """
    if len(password) < MIN_PASSWORD_LEN:
        return None
    session = SessionLocal()
    try:
        existing = session.scalar(select(User).where(User.login == login))
        if existing is not None:
            return None
        user = User(
            login=login,
            password_hash=hash_password(password),
            role=role,
            full_name=full_name or login,
            secret_word=secret_word.strip(),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    finally:
        session.close()


def change_password(
    login: str, old_password: str, new_password: str
) -> tuple[bool, str]:
    """Меняет пароль только после проверки текущего.

    Args:
        login: логин пользователя.
        old_password: текущий пароль.
        new_password: новый пароль.

    Returns:
        Кортеж (успех, сообщение).
    """
    session = SessionLocal()
    try:
        user = session.scalar(select(User).where(User.login == login))
        if user is None or user.password_hash != hash_password(old_password):
            return False, "Текущий пароль неверен"
        if len(new_password) < MIN_PASSWORD_LEN:
            return False, f"Новый пароль короче {MIN_PASSWORD_LEN} символов"
        user.password_hash = hash_password(new_password)
        session.commit()
        return True, "Пароль изменён"
    finally:
        session.close()


def reset_password_with_secret(
    login: str, secret_word: str, new_password: str
) -> tuple[bool, str]:
    """Восстанавливает доступ по секретному слову.

    Args:
        login: логин пользователя.
        secret_word: секретное слово, заданное при регистрации.
        new_password: новый пароль.

    Returns:
        Кортеж (успех, сообщение).
    """
    session = SessionLocal()
    try:
        user = session.scalar(select(User).where(User.login == login))
        if user is None:
            return False, "Пользователь с таким логином не найден"
        stored = (user.secret_word or "").strip().lower()
        if not stored or stored != secret_word.strip().lower():
            return False, "Секретное слово не совпадает"
        if len(new_password) < MIN_PASSWORD_LEN:
            return False, f"Пароль короче {MIN_PASSWORD_LEN} символов"
        user.password_hash = hash_password(new_password)
        session.commit()
        return True, "Пароль обновлён, войдите с новым паролем"
    finally:
        session.close()


def admin_reset_password(admin: User, login: str, new_password: str) -> tuple[bool, str]:
    """Сбрасывает пароль любому пользователю — только роль admin.

    Args:
        admin: пользователь, выполняющий сброс.
        login: логин того, чей пароль сбрасывают.
        new_password: новый пароль.

    Returns:
        Кортеж (успех, сообщение).
    """
    if getattr(admin, "role", "") != "admin":
        return False, "Сброс пароля доступен только администратору"
    session = SessionLocal()
    try:
        user = session.scalar(select(User).where(User.login == login))
        if user is None:
            return False, "Пользователь с таким логином не найден"
        if len(new_password) < MIN_PASSWORD_LEN:
            return False, f"Пароль короче {MIN_PASSWORD_LEN} символов"
        user.password_hash = hash_password(new_password)
        session.commit()
        return True, "Пароль сброшен администратором"
    finally:
        session.close()
