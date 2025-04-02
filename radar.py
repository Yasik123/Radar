import re
import os
import logging
import asyncio
import threading
from flask import Flask
from telethon import TelegramClient, events

# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Данные Telegram
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
source_channel_id = int(os.getenv("SOURCE_CHANNEL_ID"))
destination_channel_id = int(os.getenv("DESTINATION_CHANNEL_ID"))

# Подключение к Telegram
client = TelegramClient("session_name", api_id, api_hash)

# Фильтры
blacklist_words = {"донат", "підтримати", "реклама", "підписка", "переказ на карту", "пожертва", "допомога", "підтримка", "збір", "задонатити"}
card_pattern = re.compile(r'\b(?:\d[ -]*){12,19}\b|\bUA\d{25,}\b')
url_pattern = re.compile(r'https?://\S+', re.IGNORECASE)
city_pattern = re.compile(r'Стежити за обстановкою .*? можна тут - \S+', re.IGNORECASE)
unwanted_text_pattern = re.compile(r'(Підтримати канал, буду вдячний Вам:|🔗Посилання на банку|➡️Підписатися)', re.IGNORECASE)
city_pattern2 = re.compile(r'Наслідки балістичного удару дивитись тут - \S+', re.IGNORECASE)

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
    text = re.sub(city_pattern, '', text)
    text = re.sub(city_pattern2, '', text)
    text = re.sub(unwanted_text_pattern, '', text)
    text = text.replace("ㅤ", "").strip()
    
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    filtered_lines = [line for line in lines if len(line.split()) > 1]  # Убираем одиночные случайные слова
    
    formatted_text = "\n\n".join(filtered_lines)
    return formatted_text

# Функция отправки и удаления фейкового сообщения
async def send_fake_message():
    try:
        fake_message = "."
        sent_message = await client.send_message(destination_channel_id, fake_message, parse_mode='html')
        await asyncio.sleep(2)
        await client.delete_messages(destination_channel_id, sent_message.id)
        logger.info("✅ Фейковое сообщение отправлено и удалено.")
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке фейкового сообщения: {e}", exc_info=True)

# Функция для периодической отправки фейковых сообщений
async def periodic_fake_message():
    while True:
        await send_fake_message()
        await asyncio.sleep(300)

# Обработчик сообщений
@client.on(events.NewMessage(chats=source_channel_id))
async def handler(event):
    try:
        logger.info("🟢 Обработчик сообщений работает")
        message_text = event.message.raw_text or ""
        message_media = event.message.media
        
        logger.info(f"📩 Новое сообщение: {message_text}")
        
        message_text = clean_message(message_text)
        
        if any(word in message_text for word in blacklist_words) or card_pattern.search(message_text):
            logger.info("🚫 Сообщение заблокировано.")
            return

        if message_text:
            message_text += f"\n\n{extra_text}"
        
        if message_media:
            await client.send_file(destination_channel_id, message_media, caption=message_text, parse_mode='html')
            logger.info("✅ Отправлено фото с текстом")
        else:
            await client.send_message(destination_channel_id, message_text, link_preview=False, parse_mode='html')
            logger.info("✅ Отправлено текстовое сообщение")
        
        await asyncio.sleep(0.1)  # Добавлена небольшая задержка для стабильности
    except Exception as e:
        logger.error(f"❌ Ошибка обработки сообщения: {e}", exc_info=True)

# Функция запуска Flask в асинхронном режиме
async def run_flask():
    loop = asyncio.get_running_loop()
    server = await loop.run_in_executor(None, lambda: app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)), debug=False, use_reloader=False))
    return server

# Основная асинхронная функция
async def main():
    asyncio.create_task(periodic_fake_message())
    asyncio.create_task(run_flask())
    
    await client.start()
    logger.info("🚀 Бот запущен и слушает канал!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
