from datetime import datetime, timedelta

import apscheduler
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from apscheduler.jobstores.base import ConflictingIdError
from apscheduler.triggers.date import DateTrigger

from db.db import Sqlbase
from keyboard.menu_fabric import InlineMainMenu, FabricInline
from schedulers.auto_exit import auto_exit
from schedulers.scheduler_object import scheduler

router_for_admin = Router()
sqlbase_for_admin_function = Sqlbase()
keyboard = FabricInline()


class UpdPassword(StatesGroup):
    newpass = State()


class UpdQueryPassword(StatesGroup):
    newpass = State()


class LoginState(StatesGroup):
    name = State()
    password = State()


@router_for_admin.callback_query(InlineMainMenu.filter(F.action == 'exit'))
async def handle_stop(callback: CallbackQuery, state: FSMContext):
    await sqlbase_for_admin_function.connect()
    await sqlbase_for_admin_function.update_state_admin(0)
    await sqlbase_for_admin_function.close()
    try:
        scheduler.remove_job(job_id="auto_exit")
    except apscheduler.jobstores.base.JobLookupError:
        pass
    kb = await keyboard.stop()
    await state.clear()
    await callback.message.answer("Вы вышли из админа", reply_markup=kb)
    await callback.answer()


@router_for_admin.callback_query(InlineMainMenu.filter(F.action == "login_in_super_admin"))
async def login(callback: CallbackQuery, state: FSMContext):
    """
    Функция для супер-админа
    :param callback:
    :param state:
    """
    await sqlbase_for_admin_function.connect()
    # Выполнение запроса для получения имени и пароля
    password = await sqlbase_for_admin_function.execute_query(
        'SELECT superuser_active, superuser_chat_id, superuser_password FROM settings_for_admin;')

    kb_super_admin = await keyboard.inline_admin_main_menu()
    kb_admin = await keyboard.inline_main_menu()
    if password[0][0] and password[0][1] == str(callback.message.chat.id):
        try:
            await callback.message.edit_text("Вы уже супер-администратор\nВыберите действие:",
                                             reply_markup=kb_super_admin)
        except TelegramBadRequest:
            pass
        await sqlbase_for_admin_function.close()
        return

    elif password[0][0]:
        try:
            await callback.message.answer("Кто-то другой под аккаунтом супер-администратора.\nВход - невозможен",
                                          reply_markup=kb_admin)
        except TelegramBadRequest:
            pass
        await sqlbase_for_admin_function.close()
        return

    else:
        kb = await keyboard.stop()
        await state.update_data(password=password[0][2])

        await callback.message.answer(
            '*ВНИМАНИЕ*, в аккаунт супер-администратора, может зайти *ТОЛЬКО* один человек\n\nВведите пароль:'
            , reply_markup=kb, parse_mode='MARKDOWN')
        await callback.answer()
        await state.set_state(LoginState.name)


@router_for_admin.message(Command(commands=["login", "Login"]))
async def login_default(message: Message, state: FSMContext):
    """
    Функция для супер-админа
    :param message:
    :param state:
    """
    await sqlbase_for_admin_function.connect()
    # Выполнение запроса для получения имени и пароля
    password = await sqlbase_for_admin_function.execute_query(
        'SELECT superuser_active, superuser_chat_id, superuser_password FROM settings_for_admin;')

    kb_super_admin = await keyboard.inline_admin_main_menu()
    kb_admin = await keyboard.inline_main_menu()
    if password[0][0] and password[0][1] == str(message.chat.id):
        await message.answer("Вы уже супер-администратор\nВыберите действие:",
                                    reply_markup=kb_super_admin)
        await sqlbase_for_admin_function.close()
        return

    elif password[0][0]:
        await message.answer("Кто-то другой под аккаунтом супер-администратора.\nВход - невозможен",
                                 reply_markup=kb_admin)
        await sqlbase_for_admin_function.close()
        return

    else:
        kb = await keyboard.stop()
        await state.update_data(password=password[0][2])

        await message.answer(
            '*ВНИМАНИЕ*, в аккаунт супер-администратора, может зайти *ТОЛЬКО* один человек\n\nВведите пароль:'
            , reply_markup=kb, parse_mode='MARKDOWN')
        await state.set_state(LoginState.name)


@router_for_admin.message(LoginState.name, F.text)
async def name(message: Message, state: FSMContext):
    user_password = message.text
    password = await state.get_value("password")

    if user_password == password:
        await sqlbase_for_admin_function.update_state_admin(message.chat.id)
        await sqlbase_for_admin_function.close()
        kb = await keyboard.inline_admin_main_menu()
        try:
            run_time = datetime.now() + timedelta(hours=1)
            scheduler.add_job(auto_exit, trigger=DateTrigger(run_date=run_time), id="auto_exit")
        except ConflictingIdError:
            pass
        await state.clear()
        await message.answer('Пароль верный, пропишите /help для полного перечня команд', reply_markup=kb)

    else:
        await message.answer('Пароль неправильный...\nВведите заново')


@router_for_admin.callback_query(InlineMainMenu.filter(F.action == "UpdPassword"))
async def upd(callback: CallbackQuery, state: FSMContext):
    """Изменение пароля"""
    await sqlbase_for_admin_function.connect()
    check_login = await sqlbase_for_admin_function.check_login()
    check_chat = await sqlbase_for_admin_function.execute_query("""SELECT superuser_chat_id FROM settings_for_admin""")
    if check_login and check_chat[0][0] == str(callback.message.chat.id):
        kb = await keyboard.stop()
        await state.update_data(keyboard_stop=kb)
        await callback.message.answer('Введите новый пароль', reply_markup=kb)
        await callback.answer()
        await state.set_state(UpdPassword.newpass)
    else:
        await callback.answer('Вы не супер-администратор, у вас нет этой функции')


@router_for_admin.message(UpdPassword.newpass, F.text)
async def new_password(message: Message, state: FSMContext):
    """Изменение пароля"""

    alt_newpassword = await state.get_value("alt_newpassword")
    kb = await state.get_value("keyboard_stop")
    if alt_newpassword is None:  # Первый ввод пароля
        if message.text.lower() == 'stop':
            await message.answer("Обновление пароля прервано.", reply_markup=kb)
            await state.clear()
        else:
            await state.update_data(alt_newpassword=message.text)  # Сохраняем первый ввод
            await message.answer('Введите ещё раз новый пароль, чтобы подтвердить.', reply_markup=kb)
    else:  # Второй ввод пароля
        if message.text.lower() == 'stop':
            await message.answer("Обновление пароля прервано.")
            await state.clear()
        elif alt_newpassword == message.text:  # При совпадении пароля
            query = 'UPDATE settings_for_admin SET superuser_password = $1 WHERE id = 1;'
            await sqlbase_for_admin_function.execute_query(query, params=(alt_newpassword,))

            await message.answer('Пароль успешно обновлён!', reply_markup=kb)
            await state.clear()
        else:  # Если пароли не совпадают
            await message.answer('Пароли не совпадают. Повторите ввод нового пароля.', reply_markup=kb)
            await state.set_state(UpdPassword.newpass)  # Возвращаем в текущее состояние


@router_for_admin.callback_query(InlineMainMenu.filter(F.action == "UpdQueryPassword"))
async def update_query(callback: CallbackQuery, state: FSMContext):
    """Изменение пароля"""
    await sqlbase_for_admin_function.connect()
    check_login = await sqlbase_for_admin_function.check_login()
    check_chat = await sqlbase_for_admin_function.execute_query("""SELECT superuser_chat_id FROM settings_for_admin""")
    if check_login and check_chat[0][0] == str(callback.message.chat.id):
        kb = await keyboard.stop()
        await state.update_data(keyboard_stop=kb)
        await callback.message.answer('Введите новый пароль для заявок', reply_markup=kb)
        await callback.answer()
        await state.set_state(UpdQueryPassword.newpass)
    else:
        await callback.answer('Вы не супер-администратор, у вас нет этой функции')


@router_for_admin.message(UpdQueryPassword.newpass, F.text)
async def new_password(message: Message, state: FSMContext):
    """Изменение пароля"""

    alt_newpassword = await state.get_value("alt_newpassword")
    kb = await state.get_value("keyboard_stop")
    if alt_newpassword is None:  # Первый ввод пароля
        if message.text.lower() == 'stop':
            await message.answer("Обновление пароля прервано.", reply_markup=kb)
            await state.clear()
        else:
            await state.update_data(alt_newpassword=message.text)  # Сохраняем первый ввод
            await message.answer('Введите ещё раз новый пароль, чтобы подтвердить.', reply_markup=kb)
    else:  # Второй ввод пароля
        if message.text.lower() == 'stop':
            await message.answer("Обновление пароля прервано.")
            await state.clear()
        elif alt_newpassword == message.text:  # При совпадении пароля
            query = 'UPDATE settings_for_admin SET password_query = $1 WHERE id = 1;'
            await sqlbase_for_admin_function.execute_query(query, params=(alt_newpassword,))

            await message.answer('Пароль успешно обновлён!', reply_markup=kb)
            await state.clear()
        else:  # Если пароли не совпадают
            await message.answer('Пароли не совпадают. Повторите ввод нового пароля.', reply_markup=kb)
            await state.set_state(UpdPassword.newpass)  # Возвращаем в текущее состояние
