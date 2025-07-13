from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

from db.db import Sqlbase
from keyboard.menu_fabric import FabricInline

help_router = Router()
help_sqlbase = Sqlbase()
keyboard_factory = FabricInline()


@help_router.message(Command(commands=["help", "Help"]))
async def command_help(message: Message):
    await help_sqlbase.connect()
    check_login = await help_sqlbase.check_login()
    check_chat = await help_sqlbase.execute_query("""SELECT superuser_chat_id FROM settings_for_admin""")
    check_admin: tuple = await help_sqlbase.execute_query("""SELECT chat_id FROM admin_list_table""")
    try:

        if check_login and check_chat[0][0] == str(message.chat.id):
            await message.reply("Команды для администраторов:\n"
                                "/start - если что-то <b>координально</b> не работает, к примеру, раньше та или иная кнопка - работала, а теперь - нет\n",
                                parse_mode=ParseMode.HTML)
        elif check_admin.index((str(message.chat.id),)):
            await message.reply("Команды для администраторов:\n"
                                "/start - если что-то <b>координально</b> не работает, к примеру, раньше та или иная кнопка - работала, а теперь - нет\n",
                                parse_mode=ParseMode.HTML)

    except ValueError:
        await message.reply("Команды, для обычных пользователей:\n"
                            "/start - для создания заявки на администратора"
                            )
    await help_sqlbase.close()
