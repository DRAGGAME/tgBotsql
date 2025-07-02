from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from apscheduler.jobstores.base import ConflictingIdError
from apscheduler.triggers.date import DateTrigger

from db.db import Sqlbase
from schedulers.auto_exit import auto_exit
from schedulers.scheduler_object import scheduler

router_for_admin = Router()
sqlbase_for_admin_function = Sqlbase()


class UpdPassword(StatesGroup):
    newpass = State()


class LoginState(StatesGroup):
    name = State()
    password = State()

@router_for_admin.message(F.text.lower() == 'exit')
async def handle_stop(message: Message, state: FSMContext):
    await sqlbase_for_admin_function.connect()
    await sqlbase_for_admin_function.update_state_admin(False)
    await sqlbase_for_admin_function.close()
    scheduler.remove_job(job_id="auto_exit")
    await state.clear()
    await message.answer("Вы вышли из админа")

@router_for_admin.message(Command('Login'))
async def login(message: Message, state: FSMContext):

    """
    Функция для супер-админа
    :param message:
    :param state:
    """
    await sqlbase_for_admin_function.connect()
    # Выполнение запроса для получения имени и пароля
    password = await sqlbase_for_admin_function.execute_query('SELECT superuser_password FROM settings_for_admin;')

    await state.update_data(password=password[0][0])

    await message.answer('*ВНИМАНИЕ*, в аккаунт супер-администратора, может зайти *ТОЛЬКО* один человек\n\nВведите пароль:'
                         , parse_mode='MARKDOWN')
    await state.set_state(LoginState.name)


@router_for_admin.message(LoginState.name, F.text)
async def name(message: Message, state: FSMContext):

    user_password = message.text
    password = await state.get_value("password")

    if user_password == 'stop':
        await message.answer('Вход завершён принудительно')
        await state.clear()
        await sqlbase_for_admin_function.close()
        return

    if user_password == password:
        await sqlbase_for_admin_function.update_state_admin(True)
        await sqlbase_for_admin_function.close()
        try:
            run_time = datetime.now() + timedelta(hours=1)
            scheduler.add_job(auto_exit, trigger=DateTrigger(run_date=run_time), id="auto_exit")
        except ConflictingIdError:
            pass
        await state.clear()
        await message.answer('Пароль верный, пропишите /help для полного перечня команд')

    else:
        await message.answer('Пароль неправильный...')

@router_for_admin.message(Command('UpdPassword'))
async def upd(message: Message, state: FSMContext):
    """Изменение пароля"""
    await sqlbase_for_admin_function.connect()
    check_login = await sqlbase_for_admin_function.check_login()
    if check_login:
        await message.answer('Введите новый пароль')
        await state.set_state(UpdPassword.newpass)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')


@router_for_admin.message(UpdPassword.newpass, F.text)
async def new_password(message: Message, state: FSMContext):
    """Изменение пароля"""

    alt_newpassword = await state.get_value("alt_newpassword")

    if alt_newpassword is None:  # Первый ввод пароля
        if message.text.lower() == 'stop':
            await message.answer("Обновление пароля прервано.")
            await state.clear()
        else:
            await state.update_data(altnewpass=message.text)  # Сохраняем первый ввод
            await message.answer('Введите ещё раз новый пароль, чтобы подтвердить.')
    else:  # Второй ввод пароля
        if message.text.lower() == 'stop':
            await message.answer("Обновление пароля прервано.")
            await state.clear()
        elif alt_newpassword == message.text: #При совпадении пароля
            query = 'UPDATE adm SET password = $1 WHERE id = 1;'
            await sqlbase_for_admin_function.execute_query(query, params=(alt_newpassword,))
            await message.answer('Пароль успешно обновлён!')
            await state.clear()
        else:  # Если пароли не совпадают
            await message.answer('Пароли не совпадают. Повторите ввод нового пароля.')
            await state.set_state(UpdPassword.newpass)  # Возвращаем в текущее состояние