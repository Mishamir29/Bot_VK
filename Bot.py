import os
import database
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from apscheduler.schedulers.background import BackgroundScheduler
from database import  register_user, get_user_name, log_arrival, log_departure
from reports import generate_monthly_report
from config import TOKEN, ADMIN_ID

# Инициализация ВК
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)


def send_file(user_id, file_path, message_text="📊 Ваш отчёт готов!"):
    """Отправляет документ пользователю ВК."""
    try:
        upload = vk_api.VkUpload(vk_session)
        doc = upload.document_message(file_path, title="Report.xlsx", peer_id=user_id)
        attachment = f"doc{doc['doc']['owner_id']}_{doc['doc']['id']}"
        vk.messages.send(
            user_id=user_id, message=message_text, attachment=attachment, random_id=0
        )
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)



# Фоновая задача планировщика (APScheduler)


def admin_monthly_job():
    """Фоновая задача: отправка отчёта начальнику 1-го числа месяца."""
    print("Запуск автоматической генерации отчёта для директора...")
    file = generate_monthly_report(for_admin=True)
    if file:
        send_file(
            ADMIN_ID,
            file,
            message_text="🔔 Автоматический отчёт по всем сотрудникам за прошлый месяц.",
        )
    else:
        vk.messages.send(
            user_id=ADMIN_ID,
            message="🔔 Автоматический отчёт: за прошлый месяц нет данных.",
            random_id=0,
        )


## Клавиатуры и обработка входящих сообщений

# Главная клавиатура
main_keyboard = VkKeyboard(one_time=False)
main_keyboard.add_button("🟢 Пришёл/Пришла", color=VkKeyboardColor.POSITIVE)
main_keyboard.add_button("🔴 Ушёл/Ушла", color=VkKeyboardColor.NEGATIVE)
main_keyboard.add_line()
main_keyboard.add_button("📊 Получить отчёт", color=VkKeyboardColor.PRIMARY)

print("Сава запущен...")

if __name__ == "__main__":
    database.init_db()

    # Настройка планировщика: запуск 1-го числа каждого месяца в 09:00
    scheduler = BackgroundScheduler()
    scheduler.add_job(admin_monthly_job, "cron", day=1, hour=9, minute=0)
    scheduler.start()

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
            text = event.text.strip()
            uid = event.user_id

            # Проверяем регистрацию сотрудника
            user_name = get_user_name(uid)

            if not user_name:
                # Если пишет в первый раз, запрашиваем ФИО
                if text.lower() in ["начать", "привет", "старт"]:
                    vk.messages.send(
                        user_id=uid,
                        message="Здравствуйте! Вы не зарегистрированы в системе.\n\nПожалуйста, отправьте ваше ФИО в ответном сообщении (Например: Иванов Иван Иванович).",
                        random_id=0,
                    )
                else:
                    # Любой текст после приветствия считается за ФИО
                    register_user(uid, text)
                    vk.messages.send(
                        user_id=uid,
                        message=f"Регистрация успешна!\nВы записаны как: {text}\nИспользуйте кнопки снизу для учёта времени.",
                        keyboard=main_keyboard.get_keyboard(),
                        random_id=0,
                    )
                continue

            # Логика для зарегистрированных сотрудников
            if text.lower() == "🟢 пришёл/пришла":
                reply = log_arrival(uid)
                vk.messages.send(
                    user_id=uid,
                    message=reply,
                    keyboard=main_keyboard.get_keyboard(),
                    random_id=0,
                )

            elif text.lower() == "🔴 ушёл/ушла":
                reply = log_departure(uid)
                vk.messages.send(
                    user_id=uid,
                    message=reply,
                    keyboard=main_keyboard.get_keyboard(),
                    random_id=0,
                )

            elif text.lower() == "📊 получить отчёт":
                file = generate_monthly_report(for_admin=False)
                if file:
                    send_file(
                        uid,
                        file,
                        message_text="📊 Ваш персональный отчёт за текущий месяц:",
                    )
                else:
                    vk.messages.send(
                        user_id=uid,
                        message="Записей за этот месяц пока нет.",
                        random_id=0,
                    )
