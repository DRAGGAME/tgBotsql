from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from db.db import Sqlbase
from keyboard.menu_fabric import InlineMainMenu, FabricInline

router_for_admin_function = Router()
sqlbase_admin_function = Sqlbase()
keyboard_fabric = FabricInline()


class NameBot(StatesGroup):
    name = State()


@router_for_admin_function.callback_query(InlineMainMenu.filter(F.action == "edit_name"))
async def new_name(callback: CallbackQuery, state: FSMContext):
    """Обновление имени бота"""
    await sqlbase_admin_function.connect()
    check_login = await sqlbase_admin_function.check_login()
    check_chat = await sqlbase_admin_function.execute_query("""SELECT superuser_chat_id FROM settings_for_admin""")
    if check_login and check_chat[0][0] == str(callback.message.chat.id):

        await callback.message.answer('Напишите имя бота')
        await callback.answer()
        await state.set_state(NameBot.name)

    else:
        await callback.answer('Вы не супер-администратор, у вас нет этой функции')


@router_for_admin_function.message(NameBot.name, F.text)
async def name(message: Message, state: FSMContext):
    kb = await keyboard_fabric.inline_admin_main_menu()
    if message.text.lower() == 'стоп':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс изменения имени клиентского бота.", reply_markup=kb)
        await state.clear()
    else:
        await state.update_data(name=message.text)
        data = await state.get_data()
        await sqlbase_admin_function.connect()
        await sqlbase_admin_function.execute_query('''UPDATE settings_for_admin SET bot_name = $1''', (data['name'],))
        await sqlbase_admin_function.close()
        await message.answer('Имя перезаписано', reply_markup=kb)
