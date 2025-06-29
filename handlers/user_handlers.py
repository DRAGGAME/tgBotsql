from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message

from db.db import Sqlbase
from keyboard.fabirc_kb import KeyboardFactory


class AnswerForAdmin(StatesGroup):
    accept = State()
    password = State()


user_router = Router()
user_sqlbase = Sqlbase()
keyboard = KeyboardFactory()

@user_router.message(F.text.lower()=='отправить новую заявку')
@user_router.message(CommandStart())
async def check_user_in_admin(message: Message, state: FSMContext):
    chat_id = message.chat.id

    await user_sqlbase.connect()

    check_user = await user_sqlbase.execute_query("""SELECT * FROM admin_list_table WHERE chat_id=$1""", (str(chat_id), ))
    if check_user:
        await message.answer("Вы уже записаны")
        await user_sqlbase.close()

    else:
        await state.set_state(AnswerForAdmin.accept)
        kb = await keyboard.builder_reply_choice("Хотите отправить заявку на добавление в администраторы?")
        await message.answer('Здравствуйте, если вы хотите отправить заявку на добавление в администраторы, '
                             'то заранее измените настройки конфиденциальности, в разделе "О себе", измените выбор на "Все"',
                             reply_markup=kb)

@user_router.message(AnswerForAdmin.accept, F.text.lower().contains('да'))
async def yes_for_answer(message: Message, state: FSMContext):

    password_session = await user_sqlbase.execute_query("""SELECT password_query FROM settings_for_admin""")
    await state.update_data(password=password_session[0][0])
    await state.set_state(AnswerForAdmin.password)
    await message.answer("Введите пароль для возможности отправки заявки")

@user_router.message(AnswerForAdmin.password)
@user_router.message(F.text.lower()=='отправить')
async def password_state(message: Message, state: FSMContext):

    if not message.text:
        await message.answer("Это сообщение - не текст")
        return

    password = await state.get_value("password")
    user_password = await state.get_value('user_password')

    username = message.from_user.username
    chat_id = message.chat.id

    if user_password:
        await state.clear()
        await user_sqlbase.insert_new_query(chat_id, username)
        await message.answer("Мы отправили запрос. Вы получите уведомление, как только оно будет принято")
        return

    user_password = message.text

    if user_password == password:
        if username is None:
            kb = await keyboard.builder_reply_query()
            await state.update_data(user_password=user_password)
            await message.answer('Ваше имя пользователя скрыто, мы не можем отправить запрос, измените настройку и кнопку "отправить"'
                                 , reply_markup=kb)
            return

        await state.clear()
        await user_sqlbase.insert_new_query(chat_id, username)
        await message.answer("Мы отправили запрос. Вы получите уведомление, как только оно будет принято")
    else:
        kb = await keyboard.builder_reply_new_query()

        await user_sqlbase.close()
        await state.clear()
        await message.answer("Пароль - неправильный. Нажмите кнопку, чтобы отправить заявку заново", reply_markup=kb)

