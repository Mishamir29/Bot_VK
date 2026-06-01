FROM dockerhub.timeweb.cloud/library/python:3.10-slim

WORKDIR /app

# Устанавливаем системные зависимости для корректной работы со временем в Linux
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

# Копируем и устанавливаем асинхронные зависимости через ПРАВИЛЬНОЕ зеркало Яндекса
RUN pip install --no-cache-dir vkwave aiosqlite openpyxl apscheduler 
#-i https://yandex.ru --trusted-host mirror.yandex.ru

COPY . .

CMD ["python", "Bot.py"]
