import logging
import asyncio
import os
import psycopg2
from aiogram.filters import CommandStart
from aiogram.types import Message
from psycopg2 import Error
import select
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from config import ip, PG_password, PG_user, DATABASE

logging.basicConfig(level=logging.INFO)

connection = psycopg2.connect(host=ip, user=PG_user, password=PG_password, database=DATABASE)
load_dotenv()
bot = Bot(token=os.getenv('API_KEY'))
dp = Dispatcher()

# Переменная для отслеживания последнего обработанного ID
last_processed_id = 0


@dp.message(CommandStart)
async def cnd(message: Message):
    await message.answer('топ')


async def start_cmd():
    global last_processed_id
    connection.autocommit = True
    try:
        with connection.cursor() as cur:
            cur.execute(f"LISTEN {PG_user};")
            print("Ожидание уведомлений о новых данных...")
            cur.execute(f"SELECT adm_one, adm_too, adm_three FROM adm ORDER BY id DESC LIMIT 1;")
            rows = cur.fetchall()
            admins = []
            for row in rows[0]:
                if row is not None:
                    admins.append(row)
            cur.execute("SELECT MAX(id) FROM servers;")
            result = cur.fetchone()
            if result and result[0]:
                last_processed_id = result[0]

            while True:
                if select.select([connection], [], [], 5) == ([], [], []):
                    continue

                connection.poll()
                while connection.notifies:
                    notify = connection.notifies.pop(0)
                    cur.execute(f"SELECT id, Data_times, Place, Id_user, Rating, Review FROM servers WHERE id > {last_processed_id} ORDER BY id ASC;")
                    rows = cur.fetchall()

                    for row in rows:
                        message = (f"Дата: {row[1]}\n"
                                   f"Место: {row[2]}\n"
                                   f"Пользователь(id): {row[3]}\n"
                                   f"Рейтинг: {row[4]}\n"
                                   f"Отзыв: {row[5]}")
                        for admin_id in admins:
                            await bot.send_message(chat_id=admin_id, text=message)
                        last_processed_id = row[0]

    except Error as e:
        connection.rollback()
        print(f"Transaction failed: {str(e)}")


async def start_c():
    await start_cmd()


async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(start_c, IntervalTrigger(seconds=60))
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
