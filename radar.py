import re
import os
import logging
import asyncio
import random
from collections import deque
from flask import Flask
from telethon import TelegramClient, events

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Данные Telegram
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
source_channel_id = int(os.getenv("SOURCE_CHANNEL_ID"))
destination_channel_id = int(os.getenv("DESTINATION_CHANNEL_ID"))

# Инициализация Telegram клиента
client = TelegramClient("session_name", api_id, api_hash)

# Очередь сообщений
message_queue = deque()

# Фильтры
blacklist_words = {"донат", "підтримати", "реклама", "підписка", "переказ на карту", "пожертва", "допомога", "підтримка", "збір", "задонатити"}
card_pattern = re.compile(r'\b(?:\d[ -]*){12,19}\b|\bUA\d{25,}\b')
url_pattern = re.compile(r'https?://\S+', re.IGNORECASE)
unwanted_text_pattern = re.compile(r'(Україна Online \| Підписатись.*|Підтримати канал, буду вдячний Вам:|🔗Посилання на банку|➡️Підписатися)', re.IGNORECASE)

extra_text = '🇺🇦 <a href="https://t.me/+9RxqorgcHYZkYTQy">Небесний Вартовий</a>'

# Flask API
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

@app.route('/health')
def health():
    return "OK", 200

# Функция очистки и форматирования сообщения
def clean_message(text):
    text = re.sub(url_pattern, '', text)
    text = re.sub(unwanted_text_pattern, '', text)
    text = text.replace("ㅤ", "").strip()

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    filtered_lines = [line for line in lines if len(line.split()) > 1]

    if filtered_lines:
        filtered_lines[0] = f"<b>{filtered_lines[0]}</b>"

    return "\n\n".join(filtered_lines)

# Отправка фейкового сообщения
async def send_fake_message():
    try:
        fake_message = "."
        sent_message = await client.send_message(destination_channel_id, fake_message)
        await asyncio.sleep(2)
        await client.delete_messages(destination_channel_id, sent_message.id)
        logger.info("💬 Фейковое сообщение отправлено и удалено.")
    except Exception as e:
        logger.error(f"Ошибка при отправке фейкового сообщения: {e}", exc_info=True)

# Периодическая отправка фейков
async def periodic_fake_message():
    while True:
        await send_fake_message()
        await asyncio.sleep(300)  # Каждые 5 минут

# Обработка новых сообщений
@client.on(events.NewMessage(chats=source_channel_id))
async def handler(event):
    try:
        message_text = event.message.raw_text or ""
        message_media = event.message.media

        logger.info(f"📩 Новое сообщение: {message_text[:60]}...")

        message_text = clean_message(message_text)

        if any(word in message_text for word in blacklist_words) or card_pattern.search(message_text):
            logger.info("🚫 Сообщение заблокировано.")
            return

        if message_text:
            message_text += f"\n\n{extra_text}"

        message_queue.append((message_text, message_media))
        logger.info(f"📥 Добавлено в очередь. Размер: {len(message_queue)}")

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)

# Отправка сообщений из очереди
async def process_message_queue():
    while True:
        if message_queue:
            message_text, message_media = message_queue.popleft()
            try:
                if message_media:
                    await client.send_file(destination_channel_id, message_media, caption=message_text, parse_mode='html')
                    logger.info("✅ Отправлено с медиа.")
                else:
                    await client.send_message(destination_channel_id, message_text, link_preview=False, parse_mode='html')
                    logger.info("✅ Отправлено без медиа.")
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения: {e}", exc_info=True)
        else:
            await asyncio.sleep(1)
            continue

        await asyncio.sleep(random.uniform(1, 3))  # Антиспам задержка

# Запуск Flask
async def run_flask():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)), debug=False, use_reloader=False))

# Главная функция
async def main():
    await client.start()
    logger.info("🚀 Бот запущен и подключен к Telegram")

    # Параллельные задачи
    asyncio.create_task(run_flask())
    asyncio.create_task(periodic_fake_message())
    asyncio.create_task(process_message_queue())

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
