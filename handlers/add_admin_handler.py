import asyncio

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from config import bot
from db.db import Sqlbase
from keyboard.fabirc_kb import KeyboardFactory, InlineAddAdmin

keyboard_fabric_add = KeyboardFactory()
router_add_admins = Router()
sqlbase_add_admins = Sqlbase()


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
        last_name_account = last_account[0]
        last_chat_id = last_account[1]

        accounts.pop(count)
        new_accounts = accounts
        try:
            if data_action == "accept":
                await sqlbase_add_admins.update_inactive(True, last_chat_id, )
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

