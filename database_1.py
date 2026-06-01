# database_1.py

import aiosqlite
from datetime import datetime, date

DB_NAME = "workers_time.db"

async def init_db():
    """Асинхронно создает таблицы при первом запуске бота."""
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица сотрудников
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS time_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                work_date TEXT,
                arrival_time TEXT,
                departure_time TEXT
            )
        ''')
        await db.commit()

async def get_user_name(user_id: int):
    """Проверяет регистрацию сотрудника и возвращает его ФИО."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT full_name FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def register_user(user_id: int, name: str):
    """Добавляет нового сотрудника в базу данных."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO users (user_id, full_name) VALUES (?, ?)", (user_id, name))
        await db.commit()

async def log_arrival(user_id: int) -> str:
    """
    Фиксирует время прихода. 
    Если есть незавершенная отметка, она автоматически закрывается текущим временем.
    """
    today = date.today().isoformat()
    now_time = datetime.now().strftime("%H:%M:%S")
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id, work_date, arrival_time FROM time_logs WHERE user_id = ? AND departure_time IS NULL", 
            (user_id,)
        ) as cursor:
            open_shift = await cursor.fetchone()
        
        extra_msg = ""
        # Если нашли незакрытый приход — принудительно проставляем ему уход
        if open_shift:
            shift_id, old_date, old_arr = open_shift
            await db.execute(
                "UPDATE time_logs SET departure_time = ? WHERE id = ?",
                (now_time, shift_id)
            )
            extra_msg = f"⚠️ Предыдущий приход [{old_arr}] автоматически завершён в {now_time}.\n\n"
        
        # Создаем новую строчку для свежего прихода
        await db.execute(
            "INSERT INTO time_logs (user_id, work_date, arrival_time) VALUES (?, ?, ?)",
            (user_id, today, now_time)
        )
        await db.commit()
        return f"{extra_msg}✅ Зафиксирован НОВЫЙ приход: {now_time}"

async def log_departure(user_id: int) -> str:
    """Фиксирует время ухода для последнего открытого прихода."""
    now_time = datetime.now().strftime("%H:%M:%S")
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id FROM time_logs WHERE user_id = ? AND departure_time IS NULL", 
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            
            if not row:
                return "⚠️ Сначала отметьте приход (нажмите кнопку '🟢 Пришёл')!"
            
            shift_id = row[0]
        
        # Обновляем уход для найденного интервала
        await db.execute(
            "UPDATE time_logs SET departure_time = ? WHERE id = ?",
            (now_time, shift_id)
        )
        await db.commit()
        return f"🚪 Время ухода зафиксировано: {now_time}"
