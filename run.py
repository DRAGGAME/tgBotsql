import logging
import asyncio

from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.triggers.interval import IntervalTrigger

from config import bot
from db.connect_sqlbase_for_sheduler import sqlbase_for_scheduler
from db.create_table import CreateTable
from handlers.administrarion_handlers.function_for_admin import router_admin_function
from handlers.super_administration_handlers.add_admin_handler import router_add_admins
from handlers.super_administration_handlers.address_handlers import router_for_places
from handlers.super_administration_handlers.super_admin_function import router_for_admin_function
from handlers.super_administration_handlers.all_a_administraors_handler import router_for_admin
from schedulers.backid import back_id
from schedulers.starts import start_cmd
from handlers.user_handlers import user_router
from schedulers.scheduler_object import scheduler

logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] #%(levelname)-4s %(filename)s:'
                    '%(lineno)d - %(name)s - %(message)s'
                    )

dp = Dispatcher()

dp.include_routers( user_router, router_add_admins, router_for_places, router_for_admin, router_for_admin_function,
                    router_admin_function)

async def main():
    """
    Создание таблиц
    Создание шедулеров
    :return:
    """
    try:
        run_sqlbase = CreateTable()

        await sqlbase_for_scheduler.connect()
        await run_sqlbase.connect()  # Подключение к БД
        # await run_sqlbase.update_inactive(False, 0, )
        await run_sqlbase.create_table_adm_settings()
        await run_sqlbase.create_table_message()
        await run_sqlbase.create_table_settings_for_review()
        await run_sqlbase.create_table_admin_users()
        await run_sqlbase.create_table_reviews()

        chat_ids = await run_sqlbase.execute_query(
            "SELECT chat_id FROM admin_list_table WHERE activate=True ORDER BY id ASC;"
        )
        if chat_ids:
            for chat_id in chat_ids[0]:
                if chat_id not in (None, ):
                    scheduler.add_job(start_cmd, IntervalTrigger(minutes=1), args=[str(chat_id), sqlbase_for_scheduler], id=str(chat_id))
                    scheduler.add_job(back_id, IntervalTrigger(minutes=45), args=(sqlbase_for_scheduler, str(chat_id)), id=f'id_back{chat_id}')

        scheduler.start()  # Запускаем шедулер
        await dp.start_polling(bot)  # Запускаем бота

    finally:
        scheduler.shutdown()  # Останавливаем APScheduler

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass