import os
import re
import asyncio
import logging
from datetime import datetime, timedelta

from telethon import TelegramClient, events
from telethon.tl.functions.messages import SendMessageRequest, DeleteMessagesRequest

# .env переменные
api_id = 17082218
api_hash = '6015a38682c3f6265ac55a1e35b1240a'
source_channel = -1002279229082
destination_channel = -1002264693466 
admin_user_id = 7660007619

# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("RadarBot")

client = TelegramClient("radar_bot", api_id, api_hash)

last_message_time = datetime.utcnow()

# Шаблоны
subscribe_replace = '🇺🇦 <a href="https://t.me/+9RxqorgcHYZkYTQy">Небесний Вартовий</a>'
subscribe_pattern = re.compile(r"➡️Підписатися.*", re.IGNORECASE)
tme_links_pattern = re.compile(r"(https?://t\.me/\S+|\(https?://t\.me/\S+\))")
lines_to_remove = [
    re.compile(r"Підписатись.*", re.IGNORECASE),
    re.compile(r"🔗Посилання.*", re.IGNORECASE),
    re.compile(r"➡️Підписатися.*", re.IGNORECASE),
    re.compile(r"ㅤ", re.IGNORECASE),
    re.compile(r".*Подробиці.*", re.IGNORECASE),
    re.compile(r".*Стежити.*", re.IGNORECASE)
]

# Удаляет строки по шаблону
def filter_lines(text):
    lines = text.splitlines()
    clean_lines = []
    for line in lines:
        if any(p.search(line) for p in lines_to_remove):
            continue
        clean_lines.append(line.strip())
    return clean_lines

# Обработка сообщения
def process_message(text):
    text = subscribe_pattern.sub(subscribe_replace, text)
    text = tme_links_pattern.sub('', text)
    lines = filter_lines(text)
    return "<b>" + lines[0] + "</b>" if lines else None

# Фейковое сообщение
async def send_fake_message():
    try:
        msg = await client.send_message(destination_channel, ".")
        await asyncio.sleep(2)
        await client.delete_messages(destination_channel, msg.id)
        logger.info("📡 Фейковое сообщение отправлено и удалено.")
    except Exception as e:
        logger.error(f"Ошибка фейкового сообщения: {e}")

# Проверка бездействия
async def monitor_inactivity():
    global last_message_time
    while True:
        await asyncio.sleep(600)
        now = datetime.utcnow()
        if (now - last_message_time) > timedelta(minutes=10):
            try:
                await client.send_message(admin_user_id, "⚠️ БОТ бездействует более 10 минут!")
                logger.warning("📭 Отправлено предупреждение об бездействии.")
            except Exception as e:
                logger.error(f"Ошибка при отправке ЛС админу: {e}")

# Обработка новых сообщений
@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    global last_message_time
    last_message_time = datetime.utcnow()

    try:
        text = event.message.raw_text or ""
        media = event.message.media

        result = process_message(text)
        if not result:
            logger.info("🚫 Сообщение отфильтровано полностью.")
            return

        if media:
            await client.send_file(destination_channel, media, caption=result, parse_mode='html')
            logger.info("📤 Отправлено с фото: " + result)
        else:
            await client.send_message(destination_channel, result, parse_mode='html')
            logger.info("✉️ Отправлено текстовое: " + result)

    except Exception as e:
        logger.error(f"Ошибка при обработке: {e}")

# Главный цикл
async def main():
    await client.start()
    logger.info("🚀 Бот запущен.")

    # Запуск фоновых задач
    asyncio.create_task(monitor_inactivity())
    asyncio.create_task(fake_loop())

    await client.run_until_disconnected()

# Цикл фейков
async def fake_loop():
    while True:
        await send_fake_message()
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(main())
