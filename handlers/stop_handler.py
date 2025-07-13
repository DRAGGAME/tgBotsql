from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from db.db import Sqlbase
from keyboard.menu_fabric import FabricInline

keyboard_fabric = FabricInline()
router_for_stop = Router()
sqlbase = Sqlbase()


@router_for_stop.message(F.text.lower() == "стоп")
async def stop_message(message: Message, state: FSMContext):
    """
    Останавливает любой текущий процесс и возвращает в панель.
    """
    await sqlbase.connect()
    check_login = await sqlbase.check_login()
    check_chat = await sqlbase.execute_query("""SELECT superuser_chat_id FROM settings_for_admin""")
    check_admin: tuple = await sqlbase.execute_query("""SELECT chat_id FROM admin_list_table""")
    try:

        if check_login and check_chat[0][0] == str(message.chat.id):
            kb_new = await keyboard_fabric.inline_admin_main_menu()
        elif check_admin.index((str(message.chat.id),)):
            kb_new = await keyboard_fabric.inline_main_menu()
        await message.answer(
            "Операция отменена\n"
            "Панель действий:",
            reply_markup=kb_new
        )
    except ValueError:
        await message.reply("Введите /start - чтобы прислать заявку на администратора"
                            )
    await sqlbase.close()
    await state.clear()
