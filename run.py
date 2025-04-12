import logging
import asyncio
import os
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher

from config import api_key
from db.connect_sqlbase_for_sheduler import sqlbase_for_sheduler
from handlers.shedulers.backid import back_id
from handlers.shedulers.starts import start_cmd
from jobsadd.jobadd import scheduler
from apscheduler.triggers.interval import IntervalTrigger
from db.db import Sqlbase
from handlers import adminstration_handlers

logging.basicConfig(level=logging.INFO)

load_dotenv()
bot = Bot(token=api_key, parce_mode='MARKDOWN')
dp = Dispatcher()
dp.include_router(adminstration_handlers.router)

run_sqlbase = Sqlbase()


@dp.message(CommandStart())
async def start(message: Message):
    await message.reply('Введите команду /help')


@dp.message(Command('StartMessage'))
async def start_message(message: Message):
    id_user = message.from_user.id
    job = scheduler.get_job(str(id_user))

    if not job:
        # Если задача не была добавлена, добавляем её
        scheduler.add_job(start_cmd, IntervalTrigger(seconds=60), id=str(id_user))

    # Включаем задачу
    scheduler.resume_job(str(id_user))
    await message.answer('Теперь сообщения будут доставляться вам')


@dp.message(Command('StopMessage'))
async def stop_message(message: Message):
    id_user = message.from_user.id
    job = scheduler.get_job(str(id_user))
    if job:
        # Останавливаем задачу, если она существует
        scheduler.pause_job(str(id_user))
        await message.answer('Теперь сообщения не доставляются вам')
    else:
        await message.answer('Задача не была запущена.')

@dp.message(Command('Userid'))
async def user_idd(message: Message):
    await message.answer(f'ID вашего профиля в телеграм: {message.from_user.id}')


async def main():
    try:
        await sqlbase_for_sheduler.connect()
        await run_sqlbase.connect()  # Подключение к БД
        adm = await run_sqlbase.execute_query(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'adm')")
        if str(adm) in '[<Record exists=False>]':
            await run_sqlbase.execute_query('''
                CREATE TABLE IF NOT EXISTS adm (
                    Id SERIAL PRIMARY KEY,
                    adm_1 TEXT,
                    adm_2 TEXT, 
                    adm_3 TEXT, 
                    adm_4 TEXT, 
                    adm_5 TEXT, 
                    adm_6 TEXT, 
                    adm_7 TEXT, 
                    adm_8 TEXT, 
                    adm_9 TEXT,
                    adm_10 TEXT,
                    id_back1 INTEGER,
                    id_back2 INTEGER, 
                    id_back3 INTEGER, 
                    id_back4 INTEGER, 
                    id_back5 INTEGER, 
                    id_back6 INTEGER, 
                    id_back7 INTEGER, 
                    id_back8 INTEGER, 
                    id_back9 INTEGER,
                    id_back10 INTEGER,
                    name TEXT, 
                    password TEXT,
                    name_bot TEXT);
            ''')
            await run_sqlbase.execute_query('''
            INSERT INTO adm (id_back1, id_back2, id_back3, id_back4, id_back5, id_back6, id_back7, id_back8, id_back9,
            id_back10, name, password)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)''', (0, 0, 0, 0, 0 , 0, 0, 0, 0, 0 ,'12345', '12345'))
        message = await run_sqlbase.execute_query(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'message')")

        if str(message) in '[<Record exists=False>]':
            query = '''
                CREATE TABLE IF NOT EXISTS message (
                    Id SERIAL PRIMARY KEY,
                    address TEXT,
                    message TEXT,
                    photo BYTEA,
                    place TEXT);'''
            await run_sqlbase.execute_query(query)
        servers = await run_sqlbase.execute_query(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'servers')")

        if str(servers) in '[<Record exists=False>]':
            await run_sqlbase.spaltenerstellen()

        static_messages = await run_sqlbase.execute_query(
            '''SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'static_messages'
            )'''
        )

        # Проверка, существует ли таблица
        if str(static_messages) in '[<Record exists=False>]':
            query = '''CREATE TABLE IF NOT EXISTS static_message (
                Id SERIAL PRIMARY KEY,
                review_or_rating_message TEXT, 
                review_message TEXT
            );'''

            await run_sqlbase.execute_query(query)

            review_or_rating = 'Оценка принята. Если вы желаете написать отзыв, то напишите "Да", если нет, то "Нет".'
            review_message = 'Напишите, пожалуйста, отзыв'

            await run_sqlbase.execute_query(
                '''INSERT INTO static_message (review_or_rating_message, review_message) 
                   VALUES ($1, $2)''',
                (review_or_rating, review_message)
            )

        rows = await run_sqlbase.execute_query(
            "SELECT adm_1, adm_2, adm_3, adm_4, adm_5, adm_6, adm_7, adm_8, adm_9, adm_10 FROM adm ORDER BY id DESC LIMIT 1;"
        )
        for count, row in enumerate(rows[0]):
            if row not in (None, 'Нет', 'None', 'нет'):
                scheduler.add_job(start_cmd, IntervalTrigger(minutes=1), args=(str(row), count, sqlbase_for_sheduler), id=str(row))
        scheduler.add_job(back_id, IntervalTrigger(minutes=45), args=(sqlbase_for_sheduler,), id='back_id')

        scheduler.start()  # Запускаем шедулер
        await dp.start_polling(bot)  # Запускаем бота
    finally:
        scheduler.shutdown()  # Останавливаем APScheduler

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass