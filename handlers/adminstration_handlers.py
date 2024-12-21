# import os
# import aiogram
# from aiogram import Bot, Router, types, F
# from aiogram.types import Message, KeyboardButton
# from aiogram.utils.keyboard import ReplyKeyboardBuilder, ReplyKeyboardMarkup
# from aiogram.filters.command import CommandStart, Command
# from aiohttp.web_routedef import route
# from db.db_gino import Sqlbase
#
#
# sql_base = Sqlbase()
# bot = Bot(token=os.getenv('API_KEY'))
# router = Router()
#
#
# @router.message(Command('adm_panel'))
# async def adm_panel(message: Message):
#     kb = [
#         [KeyboardButton(text='Добавить пользователя')], [KeyboardButton(text='Удалить пользователя')]
#     ]
#     keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder='Введите место')
#     await message.answer('Открыта админская панель', reply_markup=keyboard)
#
#
# @router.message(F.text.in_(['Добавить пользователя']))
# async def adm_add_user(message: Message, satz):
#     x = sql_base.selectes()
#     for i in x:
#         satz += 'Айди пользователя: x[i]\n'
#     await message.answer(f'{satz}\nВведите id пользователя:')
