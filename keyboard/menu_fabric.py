from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, KeyboardButton

from keyboard.fabirc_kb import KeyboardFactory, InlineAddAdmin


class InlineMainMenu(CallbackData, prefix="main_menu"):
    action: str


class FabricInline(KeyboardFactory):

    def __init__(self):
        super().__init__()

        self.button_start = InlineKeyboardButton(
            text="Начать отправку отзывов",
            callback_data=InlineMainMenu(
                action="start_message",
            ).pack()
        )

        self.button_message_stop = InlineKeyboardButton(
            text="Остановить отправку отзывов",
            callback_data=InlineMainMenu(
                action="stop_message"
            ).pack()
        )

        self.button_generate = InlineKeyboardButton(
            text="Ссылки на места",
            callback_data=InlineMainMenu(
                action="generate_links",
            ).pack()
        )

        self.button_create_qr = InlineKeyboardButton(
            text="Создать QR-код",
            callback_data=InlineMainMenu(
                action="create_QR",
            ).pack()
        )

        self.button_review = InlineKeyboardButton(
            text="График с почасовыми оценками",
            callback_data=InlineMainMenu(
                action="reviews",
            ).pack()
        )

        self.button_stop = InlineKeyboardButton(
            text="Стоп",
            callback_data=InlineMainMenu(
                action="stop",
            ).pack()
        )



    async def inline_admin_main_menu(self):

        await self.create_builder_inline()

        button_add_admin = InlineKeyboardButton(
            text="Заявки на администратора",
            callback_data=InlineMainMenu(
                action="bid_for_admin"
            ).pack()
        )

        button_add_address = InlineKeyboardButton(
            text="Добавить место",
            callback_data=InlineMainMenu(
                action="add_place",
            ).pack()
        )

        button_edit_place = InlineKeyboardButton(
            text="Изменить место",
            callback_data=InlineMainMenu(
                action="edit_place",
            ).pack()
        )

        button_remove_address = InlineKeyboardButton(
            text="Удалить адрес",
            callback_data=InlineMainMenu(
                action="remove_address",
            ).pack()
        )

        button_remove_place = InlineKeyboardButton(
            text="Удалить место",
            callback_data=InlineMainMenu(
                action="remove_place",
            ).pack()
        )

        button_new_name = InlineKeyboardButton(
            text="Изменить имя бота, отправляющего отзывы",
            callback_data=InlineMainMenu(
                action="edit_name"
            ).pack()
        )

        button_exit = InlineKeyboardButton(
            text="Выйти из супер-администратора",
            callback_data=InlineMainMenu(
                action="exit",
            ).pack()
        )

        self.builder_inline.row(self.button_start)
        self.builder_inline.row(self.button_message_stop)
        self.builder_inline.add(button_add_admin)
        self.builder_inline.add(button_add_address)
        self.builder_inline.row(button_edit_place)
        self.builder_inline.row(button_remove_address, button_remove_place)
        self.builder_inline.row(button_new_name)
        self.builder_inline.row(self.button_create_qr)
        self.builder_inline.row(self.button_review)
        self.builder_inline.row(button_exit)

        return self.builder_inline.as_markup()

    async def inline_main_menu(self):
        await self.create_builder_inline()

        button_login = InlineKeyboardButton(
            text="Войти в аккаунт супер-пользователя",
            callback_data=InlineAddAdmin(
                action="login_in_super_admin"
            ).pack()
        )

        self.builder_inline.row(self.button_start)
        self.builder_inline.row(self.button_message_stop)
        self.builder_inline.row(button_login)
        self.builder_inline.row(self.button_generate, self.button_create_qr)
        self.builder_inline.row(self.button_review)

        return self.builder_inline.as_markup()

    async def reply_menu(self):
        await self.create_builder_reply()

        self.builder_reply.add(KeyboardButton(text="Войти в супер-пользователя"))
        self.builder_reply.row(KeyboardButton(text="Открыть панель действий"))

        return self.builder_reply.as_markup(resize_keyboard=True,
                                                input_field_placeholder='Выберите сообщение, которое вы хотите изменить', is_persistent=True)

    async def stop(self):
        await self.create_builder_inline()

        self.builder_reply.add(self.button_stop)

        return self.builder_inline.as_markup()
