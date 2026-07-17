# monitor.py
from telethon import TelegramClient
from config import API_ID, API_HASH, PHONE, SESSION_NAME
from database import SessionLocal
from models import ChatMonitor
import asyncio
import json

# Глобальный клиент (можно сделать пул клиентов для масштабирования)
client = None

async def init_telegram_client():
    global client
    if client is None:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.start(PHONE)

async def check_chat_for_user(chat_monitor: ChatMonitor):
    """Проверяет один чат для одного пользователя"""
    if client is None:
        await init_telegram_client()

    try:
        entity = await client.get_entity(chat_monitor.chat_username)
        current_last_msgs = await client.get_messages(entity, limit=1)
        if not current_last_msgs:
            return chat_monitor.last_message_id

        current_last_id = current_last_msgs[0].id
        if current_last_id <= chat_monitor.last_message_id:
            return chat_monitor.last_message_id

        # Получаем новые сообщения
        messages = await client.get_messages(
            entity,
            limit=None,
            min_id=chat_monitor.last_message_id,
            max_id=current_last_id + 1
        )

        keywords = json.loads(chat_monitor.keywords) if chat_monitor.keywords else []
        new_last_id = chat_monitor.last_message_id

        for msg in reversed(messages):
            text = msg.text or ""
            sender = getattr(msg.sender, 'username', 'аноним') if msg.sender else 'неизвестно'

            # Проверяем по ключевым словам
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    # 🎯 НАЙДЕН ЛИД!
                    print(f"🎯 ЛИД для пользователя ID {chat_monitor.user_id} в чате {chat_monitor.chat_username}")
                    print(f"   Ключевое слово: '{keyword}'")
                    print(f"   От: @{sender}")
                    print(f"   Текст: {text[:100]}...")

                    # 🚨 Здесь можно добавить отправку уведомления (email, Telegram и т.д.)

            new_last_id = max(new_last_id, msg.id)

        return new_last_id

    except Exception as e:
        print(f"⚠️ Ошибка мониторинга чата {chat_monitor.chat_username}: {e}")
        return chat_monitor.last_message_id