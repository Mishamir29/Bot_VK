# Генерация Excel-отчётов
import openpyxl
from datetime import datetime, date
from openpyxl.styles import Font
from database import cursor


def generate_monthly_report(for_admin=False):
    """
    Генерирует Excel-файл.
    Если for_admin=True, возвращает общий отчёт по всем сотрудникам.
    """
    now = datetime.now()
    # Фильтр по текущему месяцу
    start_date = date(now.year, now.month, 1).isoformat()
    if now.month == 12:
        end_date = date(now.year + 1, 1, 1).isoformat()
    else:
        end_date = date(now.year, now.month + 1, 1).isoformat()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Отчёт по времени"

    # Заголовки таблицы
    headers = [
        "ID сотрудника",
        "ФИО сотрудника",
        "Дата",
        "Приход",
        "Уход",
        "Отработано",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Запрос данных с объединением (JOIN) таблиц logs и users
    cursor.execute(
        """
        SELECT u.user_id, u.full_name, t.work_date, t.arrival_time, t.departure_time
        FROM time_logs t
        JOIN users u ON t.user_id = u.user_id
        WHERE t.work_date >= ? AND t.work_date < ?
        ORDER BY u.full_name ASC, t.work_date ASC
    """,
        (start_date, end_date),
    )

    rows = cursor.fetchall()
    if not rows:
        return None

    for row in rows:
        uid, name, w_date, arr, dep = row
        hours_worked = "Не завершено"
        if arr and dep:
            t1 = datetime.strptime(arr, "%H:%M:%S")
            t2 = datetime.strptime(dep, "%H:%M:%S")
            delta = t2 - t1
            hrs = int(delta.total_seconds() // 3600)
            mins = int((delta.total_seconds() % 3600) // 60)
            hours_worked = f"{hrs}ч {mins}м"

        ws.append(
            [uid, name, w_date, arr if arr else "-", dep if dep else "-", hours_worked]
        )

    filename = (
        f"report_admin_{now.strftime('%m_%Y')}.xlsx"
        if for_admin
        else f"report_{now.strftime('%m_%Y')}.xlsx"
    )
    wb.save(filename)
    return filename
