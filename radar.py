import os
import re
import logging
import asyncio
import random
from datetime import datetime, timedelta
from collections import deque
from flask import Flask
from telethon import TelegramClient, events

# === Настройки окружения ===
api_id = 17082218
api_hash = '6015a38682c3f6265ac55a1e35b1240a'
source_channel_id = -1002279229082
destination_channel_id = -1002264693466 
owner_id = 7660007619

# === Логирование ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# === Telegram клиент ===
client = TelegramClient("radar_session", api_id, api_hash)
message_queue = deque()
last_activity_time = datetime.now()

# === Веб-сервер (для Render) ===
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Radar bot is running!", 200

def run_flask():
    port = int(os.getenv("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

# === Фейк сообщение ===
async def send_fake_message():
    try:
        sent = await client.send_message(destination_channel_id, ".")
        await asyncio.sleep(2)
        await client.delete_messages(destination_channel_id, sent.id)
        logger.info("💬 Фейк сообщение отправлено и удалено")
    except Exception as e:
        logger.error("❌ Ошибка отправки фейка", exc_info=True)

# === Периодический фейк ===
async def periodic_fake_message():
    while True:
        await send_fake_message()
        await asyncio.sleep(300)

# === Уведомление о простое ===
async def check_inactivity():
    global last_activity_time
    while True:
        if datetime.now() - last_activity_time > timedelta(minutes=10):
            try:
                await client.send_message(owner_id, "⚠️ БОТ бездействует 10 минут")
                last_activity_time = datetime.now()
            except Exception as e:
                logger.error("❌ Ошибка отправки уведомления владельцу", exc_info=True)
        await asyncio.sleep(60)

# === Обработка сообщений ===
@client.on(events.NewMessage(chats=source_channel_id))
async def handler(event):
    global last_activity_time
    try:
        msg_text = event.message.raw_text or ""
        media = event.message.media

        logger.info(f"📩 Получено сообщение: {msg_text[:60].strip()}...")

        # Удаляем встроенные ссылки
        msg_text = re.sub(r'\(https?://[^)]*\)', '', msg_text)
        msg_text = re.sub(r'https?://\S+', '', msg_text)

        # Заменяем "➡️Підписатися..." на кастомную строку
        msg_text = re.sub(r'➡️Підписатися.*', '🇺🇦 <a href="https://t.me/+9RxqorgcHYZkYTQy">Небесний Вартовий</a>', msg_text)

        # Удаляем всё после первой строки, если она содержит мусор
        lines = msg_text.strip().splitlines()
        clean_lines = [line.strip() for line in lines if line.strip()]
        if not clean_lines:
            return

        first_line = clean_lines[0]
        full_clean = []

        if "Подробиці" in msg_text:
            for line in clean_lines:
                if "Подробиці" not in line and "➡️Підписатися" not in line:
                    full_clean.append(line)
        elif len(clean_lines) > 1:
            full_clean = [first_line]
        else:
            full_clean = clean_lines

        if not full_clean:
            logger.info("🧹 Сообщение отфильтровано полностью.")
            return

        final_text = "\n\n".join(full_clean)

        # Добавим в очередь
        message_queue.append((final_text, media))
        last_activity_time = datetime.now()
        logger.info("✅ Сообщение добавлено в очередь")

    except Exception as e:
        logger.error("❌ Ошибка в обработчике сообщений", exc_info=True)

# === Отправка очереди ===
async def process_queue():
    while True:
        if message_queue:
            text, media = message_queue.popleft()
            try:
                if media:
                    await client.send_file(destination_channel_id, media, caption=text, parse_mode="html")
                    logger.info("📤 Отправлено сообщение с медиа")
                else:
                    await client.send_message(destination_channel_id, text, link_preview=False, parse_mode="html")
                    logger.info("📤 Отправлено сообщение без медиа")
            except Exception as e:
                logger.error("❌ Ошибка отправки сообщения", exc_info=True)
        await asyncio.sleep(random.uniform(1, 3))  # Задержка
        if not message_queue:
            await asyncio.sleep(1)

# === Основной запуск ===
async def main():
    await client.start()
    logger.info("🚀 Бот запущен и подключен к Telegram")

    # Запускаем задачи
    asyncio.create_task(client.run_until_disconnected())
    asyncio.create_task(process_queue())
    asyncio.create_task(periodic_fake_message())
    asyncio.create_task(check_inactivity())

    # Flask в отдельном потоке
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, run_flask)

# === Запуск ===
if __name__ == "__main__":
    asyncio.run(main())
