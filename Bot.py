import os
import asyncio
from vkwave.bots import (
    SimpleLongPollBot,
    SimpleBotEvent,
    Keyboard,
    ButtonColor,
    DocUploader,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import database_1
import reports

# Создание интерфейса клавиатуры
MAIN_KEYBOARD = Keyboard(one_time=False)
MAIN_KEYBOARD.add_text_button("🟢 Пришёл", color=ButtonColor.POSITIVE)
MAIN_KEYBOARD.add_text_button("🔴 Ушёл", color=ButtonColor.NEGATIVE)
MAIN_KEYBOARD.add_row()
MAIN_KEYBOARD.add_text_button("📊 Получить отчёт", color=ButtonColor.PRIMARY)

# Глобальный объект бота, который инициализируется внутри асинхронного цикла
bot = None


async def send_file(user_id: int, file_path: str, message_text: str):
    """Асинхронно загружает документ на сервера ВК и отправляет пользователю."""
    try:
        # Используем актуальный класс DocUploader для vkwave
        doc_uploader = DocUploader(bot.api_context)

        # Загружаем файл и получаем готовую строку вложения
        attachment_str = await doc_uploader.get_attachment_from_path(
            peer_id=user_id, file_path=file_path, title="Report.xlsx"
        )

        # Отправляем сообщение сотруднику или админу
        await bot.api_context.messages.send(
            user_id=user_id,
            message=message_text,
            attachment=attachment_str,
            random_id=0,
        )
    except Exception as e:
        print(f"❌ Ошибка при отправке файла Excel: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def admin_monthly_job():
    """Фоновая автоматическая задача: отправка отчета директору 1-го числа месяца."""
    file = await reports.generate_monthly_report(for_admin=True)
    if file:
        await send_file(
            config.ADMIN_ID,
            file,
            message_text="🔔 Автоматический сводный отчёт за прошлый месяц.",
        )
    else:
        await bot.api_context.messages.send(
            user_id=config.ADMIN_ID,
            message="🔔 Автоматический отчёт: данных за прошлый месяц нет.",
            random_id=0,
        )


async def start_application():
    """Главная асинхронная функция, которая удерживает Event Loop."""
    global bot

    try:
        # Инициализируем базу данных
        await database_1.init_db()

        # Создаем экземпляр бота строго внутри активного цикла с вашим ID группы
        bot = SimpleLongPollBot(tokens=config.TOKEN, group_id=236728953)

        # Регистрируем обработчик сообщений (Long Poll слушатель)
        @bot.message_handler()
        async def handle_all_messages(event: SimpleBotEvent):
            text = event.text.strip()
            uid = event.peer_id

            user_name = await database_1.get_user_name(uid)

            # Сценарий регистрации нового сотрудника
            if not user_name:
                if text.lower() in ["начать", "привет", "старт"]:
                    await event.answer(
                        "👋 Здравствуйте! Вы не зарегистрированы в системе.\n\nПожалуйста, отправьте ваше ФИО в ответном сообщении."
                    )
                else:
                    await database_1.register_user(uid, text)
                    await event.answer(
                        message=f"🎉 Регистрация успешна!\nВы записаны как: {text}\nИспользуйте меню для отметок.",
                        keyboard=MAIN_KEYBOARD.get_keyboard(),
                    )
                return

            # Сценарий работы кнопок для зарегистрированных пользователей
            if text == "🟢 Пришёл":
                reply = await database_1.log_arrival(uid)
                await event.answer(message=reply)

            elif text == "🔴 Ушёл":
                reply = await database_1.log_departure(uid)
                await event.answer(message=reply)

            elif text == "📊 Получить отчёт":
                # Проверяем, совпадает ли ID отправителя с ID начальника из config.py
                if uid == config.ADMIN_ID:
                    # Если это админ, генерируем общий сводный отчет за месяц (на два листа)
                    file = await reports.generate_monthly_report(for_admin=True)
                    if file:
                        await send_file(
                            uid,
                            file,
                            message_text="📊 Сводный отчёт по всем сотрудникам (Лист 1: Итоги, Лист 2: Подробные логи):",
                        )
                    else:
                        await event.answer(
                            message="📭 В базе данных пока нет записей за этот месяц."
                        )
                else:
                    # Если это обычный сотрудник, генерируем его личный отчет (на один лист)
                    file = await reports.generate_monthly_report(
                        for_admin=False, user_id=uid
                    )
                    if file:
                        await send_file(
                            uid,
                            file,
                            message_text="📊 Ваш персональный отчёт за текущий месяц:",
                        )
                    else:
                        await event.answer(
                            message="📭 У вас ещё нет записей в этом месяце."
                        )

        # Настраиваем и запускаем асинхронный планировщик задач (1 число месяца, 09:00)
        scheduler = AsyncIOScheduler()
        scheduler.add_job(admin_monthly_job, "cron", day=1, hour=9, minute=0)
        scheduler.start()

        print("Асинхронный vkwave бот запущен...")

        # Запуск Long Poll встроенным методом в фоне
        asyncio.create_task(bot.run())

        # Жестко блокируем завершение функции, чтобы контейнер не закрывался
        while True:
            await asyncio.sleep(3600)  # Засыпаем на час в бесконечном цикле

    except Exception as error:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ ЗАПУСКЕ: {error}")
        await asyncio.sleep(5)  # Даем время логам записаться


if __name__ == "__main__":
    # Инициализация стандартного Event Loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(start_application())
    except KeyboardInterrupt:
        print("\nБот успешно остановлен пользователем.")
