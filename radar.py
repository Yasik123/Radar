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
api_id = 17082218
api_hash = '6015a38682c3f6265ac55a1e35b1240a'
source_channel_id = -1002279229082
destination_channel_id = -1002264693466 

# Подключение к Telegram
client = TelegramClient("session_name", api_id, api_hash)

# Фильтры
blacklist_words = {"донат", "підтримати", "реклама", "підписка", "переказ на карту", "пожертва", "допомога", "підтримка", "збір", "задонатити"}
card_pattern = re.compile(r'\b(?:\d[ -]*){12,19}\b|\bUA\d{25,}\b')
url_pattern = re.compile(r'https?://\S+', re.IGNORECASE)
city_pattern = re.compile(r'Стежити за обстановкою .*? можна тут - \S+', re.IGNORECASE)
unwanted_text_pattern = re.compile(r'(Підтримати канал, буду вдячний Вам:|🔗Посилання на банку|➡️Підписатися)', re.IGNORECASE)

extra_text = '🇺🇦 <a href="https://t.me/+9RxqorgcHYZkYTQy">Небесний Вартовий</a>'

# Flask API
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

# Функция очистки и форматирования сообщения
def clean_message(text):
    text = re.sub(url_pattern, '', text)  # Удаление ссылок
    text = re.sub(city_pattern, '', text)  # Удаление фраз о слежении
    text = re.sub(unwanted_text_pattern, '', text)  # Удаление нежелательных фраз
    text = text.replace("ㅤ", "").strip()  # Удаление невидимых символов

    # Убираем лишние пробелы и пустые строки
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Добавляем пустую строку между абзацами
    formatted_text = "\n\n".join(lines)

    return formatted_text

# Обработчик сообщений
@client.on(events.NewMessage(chats=source_channel_id))
async def handler(event):
    try:
        message_text = event.message.raw_text or ""
        message_media = event.message.media
        
        logger.info(f"📩 Новое сообщение: {message_text}")
        
        # Очистка текста и добавление разделения абзацев
        message_text = clean_message(message_text)

        if any(word in message_text for word in blacklist_words) or card_pattern.search(message_text):
            logger.info("🚫 Сообщение заблокировано.")
            return

        if message_text:
            message_text += f"\n\n{extra_text}"
        
        # Отправка сообщения
        try:
            if message_media:
                await client.send_file(destination_channel_id, message_media, caption=message_text, parse_mode='html')
                logger.info("✅ Отправлено фото с текстом")
            else:
                await client.send_message(destination_channel_id, message_text, link_preview=False, parse_mode='html')
                logger.info("✅ Отправлено текстовое сообщение")
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке: {e}")
    
    except Exception as e:
        logger.error(f"❌ Ошибка обработки сообщения: {e}")

# Функция запуска Flask
def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)), debug=False, use_reloader=False)

# Основная асинхронная функция
async def main():
    await client.start()
    logger.info("🚀 Бот запущен и слушает канал!")
    await client.run_until_disconnected()

# Запуск сервера и бота
if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Запускаем Telegram-бота
    asyncio.run(main())
