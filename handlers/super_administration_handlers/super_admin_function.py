from uuid import uuid4

import qrcode
from aiofiles import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, FSInputFile
from apscheduler.triggers.interval import IntervalTrigger
from matplotlib import pyplot as plt

from config import bot
from db.db import Sqlbase
from function.generate_link import generate_deep_link
from schedulers.scheduler_object import scheduler
from schedulers.starts import start_cmd

router_for_admin_function = Router()
sqlbase_admin_function = Sqlbase()


class NameBot(StatesGroup):
    name = State()


@router_for_admin_function.message(Command('New_name'))
async def new_name(message: Message, state: FSMContext):
    """Обновление имени бота"""
    await sqlbase_admin_function.connect()
    check_login = await sqlbase_admin_function.check_login()
    if check_login:

        await message.answer('Напишите имя бота')
        await state.set_state(NameBot.name)

    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')

@router_for_admin_function.message(NameBot.name, F.text)
async def name(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс изменения имени клиентского бота.")
        await state.clear()
    else:
        await state.update_data(name=message.text)
        data = await state.get_data()
        await sqlbase_admin_function.connect()
        await sqlbase_admin_function.execute_query('''UPDATE adm SET name_bot = $1''', (data['name'],))
        await sqlbase_admin_function.close()
        await message.answer('Имя перезаписано')
