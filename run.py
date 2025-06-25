import logging
import asyncio

from aiogram import Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from apscheduler.triggers.interval import IntervalTrigger

from config import bot
from db.connect_sqlbase_for_sheduler import sqlbase_for_sheduler
from db.create_table import CreateTable
from handlers.shedulers.backid import back_id
from handlers.shedulers.starts import start_cmd
from jobsadd.jobadd import scheduler
from db.db import Sqlbase
from handlers import adminstration_handlers


logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] #%(levelname)-4s %(filename)s:'
                    '%(lineno)d - %(name)s - %(message)s'
                    )

dp = Dispatcher()
dp.include_router(adminstration_handlers.router)

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
        run_sqlbase = CreateTable()

        await sqlbase_for_sheduler.connect()
        await run_sqlbase.connect()  # Подключение к БД
        await run_sqlbase.create_table_adm_settings()
        await run_sqlbase.create_table_settings_for_review()
        await run_sqlbase.create_table_admin_users()
        await run_sqlbase.create_table_reviews()

        rows = await run_sqlbase.execute_query(
            "SELECT user_id FROM admin_list_table ORDER BY id ASC;"
        )
        if rows:
            for count, row in enumerate(rows[0]):
                if row not in (None, 'Нет', 'None', 'нет'):
                    scheduler.add_job(start_cmd, IntervalTrigger(minutes=1), args=(str(row), count, sqlbase_for_sheduler), id=str(row))
            scheduler.add_job(  back_id, IntervalTrigger(minutes=45), args=(sqlbase_for_sheduler,), id='id_back')

        scheduler.start()  # Запускаем шедулер
        await dp.start_polling(bot)  # Запускаем бота

    finally:
        scheduler.shutdown()  # Останавливаем APScheduler

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass