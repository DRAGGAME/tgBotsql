import logging
import asyncio
import os
import psycopg2
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from psycopg2 import Error
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from config import ip, PG_password, PG_user, DATABASE
from db.db_gino import Sqlbase
from handlers import adminstration_handlers

logging.basicConfig(level=logging.INFO)

connection = psycopg2.connect(host=ip, user=PG_user, password=PG_password, database=DATABASE)
load_dotenv()
bot = Bot(token=os.getenv('API_KEY'))
dp = Dispatcher()
dp.include_router(adminstration_handlers.router)

# Переменная для отслеживания последнего обработанного ID
outs = 1
sqlbase = Sqlbase()

# Создание глобального шедулера
scheduler = AsyncIOScheduler()


async def conn():
    await sqlbase.connect()


@dp.message(CommandStart())
async def start(message: Message):
    await message.reply('Введите команду /help')


@dp.message(Command('StartMessage'))
async def start_message(message: Message):
    job = scheduler.get_job('nice')

    if not job:
        # Если задача не была добавлена, добавляем её
        scheduler.add_job(start_cmd, IntervalTrigger(seconds=10), id='nice')

    # Включаем задачу
    scheduler.resume_job('nice')
    await message.answer('Теперь сообщения будут доставляться вам')


@dp.message(Command('StopMessage'))
async def stop_message(message: Message):
    job = scheduler.get_job('nice')

    if job:
        # Останавливаем задачу, если она существует
        scheduler.pause_job('nice')
        await message.answer('Теперь сообщения не доставляются вам')
    else:
        await message.answer('Задача не была запущена.')


async def start_cmd():
    connection.autocommit = True
    try:
        with connection.cursor() as cur:
            cur.execute(f"LISTEN {PG_user};")
            cur.execute(
                f"SELECT adm_1, adm_2, adm_3, adm_4, adm_5, adm_6, adm_7, adm_8, adm_9, adm_10, id_back FROM adm ORDER BY id DESC LIMIT 1;")
            rows = cur.fetchall()
            admins = []
            for row in rows[0]:
                admins.append(row)
            last_processed_id = admins[10]

            cur.execute(
                f"SELECT id, Data_times, Place, Id_user, Rating, Review FROM servers WHERE id > {last_processed_id} ORDER BY id ASC;")
            rows = cur.fetchall()
            cur.execute("SELECT MAX(id) FROM servers;")
            result = cur.fetchone()

            if result and result[0]:
                last_processed_id = result[0]
                last_processed_id = str(last_processed_id)
                last_processed_id = last_processed_id.replace(',', '')
                cur.execute("UPDATE adm SET id_back =%s WHERE id=1", (last_processed_id,))

            for row in rows:
                message = (f"Дата: {row[1]}\n"
                           f"Место: {row[2]}\n"
                           f"Пользователь(id): {row[3]}\n"
                           f"Рейтинг: {row[4]}\n"
                           f"Отзыв: {row[5]}")
                for admin_id in admins[0:2]:
                    if admin_id != 'None':
                        await bot.send_message(chat_id=admin_id, text=message)

    except Error as e:
        connection.rollback()
        print(f"Transaction failed: {str(e)}")


async def main():
    await conn()

    # Добавляем задачу по умолчанию
    scheduler.add_job(start_cmd, IntervalTrigger(seconds=60), id='nice')

    # Стартуем шедулер, задача будет активна по умолчанию
    scheduler.start()

    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
