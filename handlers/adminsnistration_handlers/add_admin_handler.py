import asyncio

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from apscheduler.triggers.interval import IntervalTrigger

from config import bot
from db.connect_sqlbase_for_sheduler import sqlbase_for_scheduler
from db.db import Sqlbase
from keyboard.fabirc_kb import KeyboardFactory, InlineAddAdmin
from schedulers.scheduler_object import scheduler
from schedulers.starts import start_cmd

keyboard_fabric_add = KeyboardFactory()
router_add_admins = Router()
sqlbase_add_admins = Sqlbase()

@router_add_admins.message(Command('check_new_user'))
async def adds_admins(message: Message, state: FSMContext):
    """Добавление админов"""
    await sqlbase_add_admins.connect()
    check_login = await sqlbase_add_admins.check_login()
    if check_login:
        not_active_accounts = await sqlbase_add_admins.execute_query("""SELECT username, chat_id FROM admin_list_table WHERE activate=False""")
        if not_active_accounts:
            kb = await keyboard_fabric_add.builder_inline_add_admins()
            await state.update_data(keyboard_check=kb)
            await state.update_data(not_active_accounts=list(not_active_accounts), count_for_accounts=0)
            await message.answer(f"Вот все заявки на администраторов:\n"
                                 f"Заявка от пользователя: {not_active_accounts[0][0]}",
                                 reply_markup=kb)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')

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
                scheduler.add_job(start_cmd, IntervalTrigger(minutes=1), args=[str(last_chat_id), sqlbase_for_scheduler],
                                  id=str(last_chat_id))

                await bot.send_message(chat_id=last_chat_id, text="Вашу заявку приняли, теперь вы - действующий администратор")
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

