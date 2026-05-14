import sqlite3
import datetime
from datetime import datetime, date

# Инициализация БД
conn = sqlite3.connect("workers_time.db", check_same_thread=False)
cursor = conn.cursor()


# Создание таблиц
def init_db():
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS time_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            work_date TEXT,
            arrival_time TEXT,
            departure_time TEXT,
            UNIQUE(user_id, work_date)
        )
    """
    )
    conn.commit()


# Функции работы с базой данных


def get_user_name(user_id):
    """Проверяет, зарегистрирован ли пользователь, и возвращает его ФИО."""
    cursor.execute("SELECT full_name FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def register_user(user_id, name):
    """Регистрирует сотрудника в системе."""
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, full_name) VALUES (?, ?)",
        (user_id, name),
    )
    conn.commit()


# Функции фиксации прихода и ухода
def log_arrival(user_id):
    """Фиксирует время прихода сотрудника."""
    today = date.today().isoformat()
    now_time = datetime.now().strftime("%H:%M:%S")
    try:
        cursor.execute(
            "INSERT INTO time_logs (user_id, work_date, arrival_time) VALUES (?, ?, ?)",
            (user_id, today, now_time),
        )
        conn.commit()
        return f"✅ Время прихода зафиксировано: {now_time}"
    except sqlite3.IntegrityError:
        return "⚠️ Вы уже отметили приход сегодня!"


def log_departure(user_id):
    """Фиксирует время ухода сотрудника."""
    today = date.today().isoformat()
    now_time = datetime.now().strftime("%H:%M:%S")

    cursor.execute(
        "SELECT arrival_time FROM time_logs WHERE user_id = ? AND work_date = ?",
        (user_id, today),
    )
    if not cursor.fetchone():
        return "⚠️ Сначала отметьте приход!"

    cursor.execute(
        "UPDATE time_logs SET departure_time = ? WHERE user_id = ? AND work_date = ?",
        (now_time, user_id, today),
    )
    conn.commit()
    return f"Время ухода зафиксировано: {now_time}"
