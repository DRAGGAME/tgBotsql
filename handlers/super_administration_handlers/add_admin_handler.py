import asyncio

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from apscheduler.triggers.interval import IntervalTrigger

from config import bot
from db.connect_sqlbase_for_sheduler import sqlbase_for_scheduler
from db.db import Sqlbase
from keyboard.fabirc_kb import KeyboardFactory, InlineAddAdmin
from keyboard.menu_fabric import InlineMainMenu
from schedulers.scheduler_object import scheduler
from schedulers.starts import start_cmd

keyboard_fabric_add = KeyboardFactory()
router_add_admins = Router()
sqlbase_add_admins = Sqlbase()


class DeleteAdmin(StatesGroup):
    admin = State()


@router_add_admins.callback_query(InlineMainMenu.filter(F.action == 'bid_for_admin'))
async def adds_admins(callback: CallbackQuery, state: FSMContext):
    """Добавление админов"""
    await sqlbase_add_admins.connect()
    check_login = await sqlbase_add_admins.check_login()
    check_chat = await sqlbase_add_admins.execute_query("""SELECT superuser_chat_id FROM settings_for_admin""")
    if check_login and check_chat == callback.message.chat.id:
        not_active_accounts = await sqlbase_add_admins.execute_query(
            """SELECT username, chat_id FROM admin_list_table WHERE activate=False""")
        if not_active_accounts:
            kb = await keyboard_fabric_add.builder_inline_add_admins()
            await state.update_data(keyboard_check=kb)
            await state.update_data(not_active_accounts=list(not_active_accounts), count_for_accounts=0)
            await callback.message.edit_text(f"Вот все заявки на администраторов:\n"
                                             f"Заявка от пользователя: {not_active_accounts[0][0]}",
                                             reply_markup=kb)
        else:
            await callback.answer("Новые заявки отсутствуют")
    else:
        await callback.message.answer('Вы не супер-администратор, у вас нет этой функции')


@router_add_admins.callback_query(InlineAddAdmin.filter(F.action.in_(["accept", "reject", ])))
async def add_admins_handler(callback: CallbackQuery, callback_data: InlineAddAdmin, state: FSMContext):
    await sqlbase_add_admins.connect()
    check_login = await sqlbase_add_admins.check_login()
    if check_login:
        data_action = callback_data.action

        accounts: list = await state.get_value("not_active_accounts")
        count: int = await state.get_value("count_for_accounts")
        kb = await state.get_value("keyboard_check")

        last_account = accounts[0]

        last_chat_id = last_account[1]

        accounts.pop(count)
        new_accounts = accounts
        try:
            if data_action == "accept":
                await sqlbase_add_admins.update_inactive(True, last_chat_id, )
                scheduler.add_job(start_cmd, IntervalTrigger(minutes=1),
                                  args=[str(last_chat_id), sqlbase_for_scheduler],
                                  id=str(last_chat_id))

                await bot.send_message(chat_id=last_chat_id,
                                       text="Вашу заявку приняли, теперь вы - действующий администратор")
            elif data_action == "reject":
                await sqlbase_add_admins.delete_admins(last_chat_id, )
                await bot.send_message(chat_id=last_chat_id, text="Вашу заявку на администратора отклонили")
        except TelegramBadRequest:
            pass

        try:
            new_account: tuple = new_accounts[count]

            await state.update_data(not_active_accounts=new_accounts)
            await state.update_data(count_for_accounts=count)

            await callback.message.edit_text(new_account[0], reply_markup=kb)

        except IndexError:
            await callback.message.edit_text("Все аккаунты проверены")
            await asyncio.sleep(3)
            await callback.message.delete()


@router_add_admins.callback_query(InlineMainMenu.filter(F.action == "delete_admin"))
async def delete_admin(callback: CallbackQuery, state: FSMContext):
    await sqlbase_add_admins.connect()
    check_login = await sqlbase_add_admins.check_login()
    check_chat = await sqlbase_add_admins.execute_query("""SELECT superuser_chat_id FROM settings_for_admin""")
    if check_login is True and check_chat[0][0] == str(callback.message.chat.id):
        admins = await sqlbase_add_admins.execute_query(
            """SELECT username, chat_id FROM admin_list_table WHERE activate=True""")
        if admins is None:
            await callback.answer("Нет действующих администраторов")
            return
        dict_admin: dict = {}
        message = ''
        for count, admin_data in enumerate(admins):
            message += f"{count}) {admin_data[0]}\n"
            dict_admin.update(f"{count}: {admin_data}")

        await state.update_data(admin_data=admin_data)
        await callback.message.answer(f"Введите цифру, чей аккаунт администртора вы хотите удалить: \n{message}")
        await callback.answer()
    else:
        await callback.message.answer("Вы не администратор")
        await callback.answer()

@router_add_admins.message(F.text, DeleteAdmin.admin)
async def delete_admin_two(message: Message, state: FSMContext):
    data: dict = await state.get_value("admin_data")
    if data.get(message.text):
        try:
            await sqlbase_add_admins.delete_admins(data.get(message.text)[1])
            await message.answer("Аккаунт удалён")
            await state.clear()
            await bot.send_message(chat_id=data.get(message.text)[1], text="Ваш аккаунт удалён из администраторов")
        except Exception as e:
            await message.answer(f"Ошибка: {e}")
    else:
        await message.answer("Такого аккаунта нет!")