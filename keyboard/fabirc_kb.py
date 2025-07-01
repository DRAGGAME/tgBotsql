from sys import prefix
from typing import Union

from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup

class InlineAddAdmin(CallbackData, prefix="AddAdmins"):
    action: str


class KeyboardFactory:

    def __init__(self):
        self.builder_reply = None

        self.builder_inline = None

    async def create_builder_reply(self) -> None:
        self.builder_reply = ReplyKeyboardBuilder()

    async def create_builder_inline(self) -> None:
        self.builder_inline = InlineKeyboardBuilder()

    async def builder_reply_choice(self, text_input: str) -> ReplyKeyboardMarkup:
        await self.create_builder_reply()
        self.builder_reply.add(KeyboardButton(text="Да✅"))
        self.builder_reply.add(KeyboardButton(text="Нет❌"))

        keyboard = self.builder_reply.as_markup(
                                       resize_keyboard=True,
                                         input_field_placeholder=text_input, is_persistent =True)
        return keyboard

    async def builder_text(self, texts: Union[tuple, list, set], input_field: str) -> ReplyKeyboardMarkup:
        await self.create_builder_reply()
        for text in texts:
            self.builder_reply.add(KeyboardButton(text=text))
        first_keyboard = self.builder_reply.as_markup(resize_keyboard=True,
                                                      input_field_placeholder=input_field)
        return first_keyboard

    async def builder_reply_cancel(self) -> ReplyKeyboardMarkup:
        await self.create_builder_reply()
        self.builder_reply.add(KeyboardButton(text='Отмена'))
        keyboard_cancel = self.builder_reply.as_markup(resize_keyboard=True,
                                                input_field_placeholder='Нажмите кнопку в случае необходимости')
        return keyboard_cancel

    async def builder_reply_query(self) -> ReplyKeyboardMarkup:
        await self.create_builder_reply()

        self.builder_reply.add(KeyboardButton(text='Отправить'))

        kb_query = self.builder_reply.as_markup(resize_keyboard=True,
                                                input_field_placeholder='Нажмите если хотите сделать новый запрос', is_persistent=True)

        return kb_query

    async def builder_reply_new_query(self) -> ReplyKeyboardMarkup:
        await self.create_builder_reply()

        self.builder_reply.add(KeyboardButton(text='Отправить новую заявку'))

        kb_new_query = self.builder_reply.as_markup(resize_keyboard=True,
                                                input_field_placeholder='Нажмите если хотите отправить новую заявку', is_persistent=True)

        return kb_new_query

    async def builder_choice(self):
        await self.create_builder_reply()

        self.builder_reply.row("Между оценкой и отзывом")
        self.builder_reply.row("После оценки")

        choice_keyboard = self.builder_reply.as_markup(resize_keyboard=True,
                                                input_field_placeholder='Выберите сообщение, которое вы хотите изменить', is_persistent=True)

        return choice_keyboard

    async def builder_inline_add_admins(self):
        await self.create_builder_inline()

        add_button = InlineKeyboardButton(
            text="Принять",
            callback_data=InlineAddAdmin(
                action="accept",
            ).pack()
        )

        cancel_button = InlineKeyboardButton(
            text="Отклонить",
            callback_data=InlineAddAdmin(
                action="reject",
            ).pack()
        )

        self.builder_inline.add(add_button)
        self.builder_inline.row(cancel_button)

        return self.builder_inline.as_markup()

