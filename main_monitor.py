from telethon import TelegramClient
from config import API_ID, API_HASH, PHONE, CHAT_ID, SESSION_NAME, CHECK_INTERVAL
import asyncio


async def monitor_chat(client, chat_identifier, last_message_id):
    """Мониторит один чат: проверяет, есть ли новые сообщения, выводит их, возвращает новый last_message_id"""
    try:
        entity = await client.get_entity(chat_identifier)
    except Exception as e:
        print(f"❌ Ошибка: не удалось найти чат {chat_identifier}. Убедись, что ты подписан на него!")
        return last_message_id

    try:
        # Получаем последнее сообщение в этом чате
        current_last_msgs = await client.get_messages(entity, limit=1)
        if not current_last_msgs:
            print(f"📭 В чате {chat_identifier} пока нет сообщений.")
            return last_message_id

        current_last_id = current_last_msgs[0].id

        # Если есть новые сообщения
        if current_last_id > last_message_id:
            # Получаем все сообщения между last_message_id и current_last_id (включительно)
            messages = await client.get_messages(
                entity,
                limit=None,
                min_id=last_message_id,
                max_id=current_last_id + 1
            )

            # Выводим в хронологическом порядке (от старых к новым)
            for msg in reversed(messages):
                text = msg.text or "[медиа/файл/стикер]"
                sender = getattr(msg.sender, 'username', 'аноним') if msg.sender else 'неизвестно'
                print(f"\n📬 Новое сообщение в чате {chat_identifier} [ID {msg.id}] от {msg.date} (от @{sender}):")
                print(f"   {text}")

            # Обновляем последний обработанный ID для этого чата
            return current_last_id

        else:
            # print(f"💤 В чате {chat_identifier} нет новых сообщений.")  # можно раскомментировать для отладки
            return last_message_id

    except Exception as e:
        print(f"⚠️ Ошибка при обработке чата {chat_identifier}: {e}")
        return last_message_id


async def main():
    # Подключаемся
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start(PHONE)

    print("✅ Авторизован. Начинаем мониторинг нескольких чатов...")

    # Инициализируем словарь: chat_id → last_message_id
    chat_last_ids = {}

    # Инициализация: получаем последнее сообщение для каждого чата
    for chat_id in CHAT_ID:
        try:
            entity = await client.get_entity(chat_id)
            last_msgs = await client.get_messages(entity, limit=1)
            if last_msgs:
                chat_last_ids[chat_id] = last_msgs[0].id
                preview_text = last_msgs[0].text or "[не текст]"
                print(f"📌 Чат {chat_id}: последнее сообщение ID {chat_last_ids[chat_id]} — {preview_text[:50]}...")
            else:
                chat_last_ids[chat_id] = 0
                print(f"📭 Чат {chat_id}: сообщений пока нет.")
        except Exception as e:
            print(f"❌ Не удалось инициализировать чат {chat_id}: {e}")
            chat_last_ids[chat_id] = 0

    # Бесконечный цикл проверки всех чатов
    while True:
        for chat_id in CHAT_ID:
            print(f"\n🔍 Проверяем чат: {chat_id}")
            new_last_id = await monitor_chat(client, chat_id, chat_last_ids[chat_id])
            chat_last_ids[chat_id] = new_last_id

        print(f"\n⏳ Спим {CHECK_INTERVAL} сек...")
        await asyncio.sleep(CHECK_INTERVAL)


# Запуск
if __name__ == "__main__":
    asyncio.run(main())