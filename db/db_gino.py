import asyncio

import psycopg2
from aiogram.client import bot
from psycopg2 import sql
from psycopg2 import Error

from config import ip, PG_user, DATABASE, PG_password
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Sqlbase:
    def __init__(self):
        self.connection = psycopg2.connect(host=ip, user=PG_user, password=PG_password, database=DATABASE)
        self.connection.autocommit=False
        self.cursor = self.connection.cursor()


    async def notify_listener():
        conn = await asyncpg.connect(**DB_PARAMS)
        await conn.add_listener('new_review', handle_new_review)
        print("Слушаем канал new_review...")

    async def handle_new_review(connection, pid, channel, payload):
        # payload содержит данные из pg_notify
        print(f"Получено уведомление: {payload}")
        # Отправляем сообщение в Telegram
        await bot.send_message(chat_id="your_chat_id", text=f"Новый отзыв: {payload}")

    async def main():
        # Запускаем слушатель уведомлений и бота
        await asyncio.gather(notify_listener(), dp.start_polling(bot))

        # finally:
        #     if self.connection:
        #         self.cursor.close()
        #         self.connection.close()
        #         print('Всё окей')
if __name__ == '__main__':

    test_sql_class = Sqlbase()

    test_sql_class.spaltenausgabe()
