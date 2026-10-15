"""Конфигурация приложения.

Содержит настройки подключения к базе данных.
Для отладки используется SQLite, для продакшена — MS SQL Server.
"""

# Строка подключения для отладки (файл базы появится рядом с проектом)
DATABASE_URL = "sqlite:///education_center.db"

# Для MS SQL Server — раскомментируйте, когда поднимете сервер:
# DATABASE_URL = (
#     "mssql+pyodbc://ваш_логин:ваш_пароль@localhost/EducationCenter"
#     "?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"
# )
