from turtledemo.sorting_animate import qsort
from uuid import uuid4

import qrcode
from aiofiles import os
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, FSInputFile
from apscheduler.triggers.interval import IntervalTrigger
from matplotlib import pyplot as plt

from config import bot
from db.db import Sqlbase
from function.generate_link import generate_deep_link
from handlers.super_administration_handlers.address_handlers import keyboard_fabric, messages
from handlers.user_handlers import keyboard
from keyboard.menu_fabric import FabricInline, InlineMainMenu
from schedulers.scheduler_object import scheduler
from schedulers.starts import start_cmd

router_admin_function = Router()
sqlbase = Sqlbase()
fabric_keyboard = FabricInline()


class QrR(StatesGroup):
    name = State()
    url = State()


@router_admin_function.message(F.text.lower() == "открыть панель действий")
async def action_menu(message: Message, state: FSMContext):
    await sqlbase.connect()
    admin_list = await sqlbase.execute_query("""SELECT chat_id FROM admin_list_table WHERE activate=True""")
    chat_id = message.chat.id
    for admin in admin_list:
        if str(chat_id) == admin[0]:
            kb = await fabric_keyboard.inline_main_menu()
            await state.update_data(menu_kb=kb)
            await message.answer("Выберите действие:", reply_markup=kb)
            return
    else:
        await message.answer("Вы не администратор. Для вас, нет панели")

@router_admin_function.callback_query(InlineMainMenu.filter(F.action=="start_message"))
async def start_message(callback: CallbackQuery):
    """
    Начать пересылку сообщений
    :param callback:
    """
    chat_id = callback.message.chat.id
    job = scheduler.get_job(str(chat_id))
    await sqlbase.connect()
    if not job:
        scheduler.add_job(start_cmd, IntervalTrigger(seconds=60), id=str(chat_id))

        scheduler.resume_job(str(chat_id))
    await callback.answer(text='Теперь сообщения будут доставляться вам')
    await sqlbase.close()


@router_admin_function.callback_query(InlineMainMenu.filter(F.action=="stop_message"))
async def start_message(callback: CallbackQuery):
    """
    Остановить пересылку сообщений
    :param callback:
    """
    chat_id = callback.message.chat.id
    job = scheduler.get_job(str(chat_id))

    if job:
        # Останавливаем задачу, если она существует
        scheduler.pause_job(str(chat_id))
        await callback.answer('Теперь сообщения не доставляются вам')
    else:
        await callback.answer('Вас нет в списке администраторов')

@router_admin_function.callback_query(InlineMainMenu.filter(F.action=="reviews"))
async def review(callback: CallbackQuery):
    await sqlbase.connect()
    admin_list = await sqlbase.execute_query("""SELECT chat_id FROM admin_list_table""")
    chat_id = callback.message.chat.id
    for admin in admin_list:
        if str(chat_id) == admin[0]:
            uuid = uuid4().hex

            data = await sqlbase.execute_query("""
                SELECT 
                    DATE_TRUNC('hour', data_times::TIMESTAMP) AS hour,
                    AVG(rating) AS average_rating
                FROM reviews
                WHERE data_times::TIMESTAMP >= NOW() - INTERVAL '24 hours'
                GROUP BY hour
                ORDER BY hour;
            """)
            if data:
                hours = [str(row['hour']).strip() for row in data]
                avg_ratings = [row['average_rating'] for row in data]

                plt.figure(figsize=(10, 6))
                plt.bar(hours, avg_ratings, width=0.3)

                # Настройка осей и подписей
                plt.xlabel('Дата')
                plt.ylabel('Оценка')
                plt.title('Средняя оценка по часам за последние 24 часа')
                plt.ylim(0, 5)
                plt.xticks(rotation=45)


                file_name = f'{uuid}.png'
                plt.tight_layout()
                plt.savefig(file_name)

                photo = FSInputFile(f'{uuid}.png')
                try:
                    await callback.message.answer_photo(photo=photo, caption='Чтобы открыть панель действий, '
                                                                         'нажмите на кнопку '
                                                                     '"Открыть панель действий"')
                except TelegramBadRequest:
                    pass
                # Удаление файла
                await os.remove(f'{uuid}.png')
                await callback.answer()
            else:
                await callback.answer('Нет данных по оценкам за 24 часа')
            await sqlbase.close()
            return
    else:
        await callback.message.edit_text(text='Ошибка: вы не администратор. Напишите /start - чтобы отправить заявку на администратора')

@router_admin_function.callback_query(InlineMainMenu.filter(F.action=="generate_links"))
async def send_deep(callback: CallbackQuery, state: FSMContext):
    """Генерация чисто ссылок"""
    await sqlbase.connect()
    admin_list = await sqlbase.execute_query("""SELECT chat_id FROM admin_list_table""")
    chat_id = callback.message.chat.id
    for admin in admin_list:
        if str(chat_id) == admin[0]:
            places = await sqlbase.execute_query("SELECT place FROM message")
            places = [row[0] for row in places]

            # Генерируем ссылки для каждого места с транслитерацией
            links = []
            for place in places:
                deep_link = await generate_deep_link(sqlbase, place)
                if deep_link is None:
                    """добавть проверку"""
                    kb = await state.get_value("menu_kb")
                    try:
                        await callback.message.edit_text(
                            "Добавьте имя бота. Попросите того, у кого есть пароль супер-пользователя,"
                            " добавить имя бота, отправляющего отзывы.\n\nВыберите действие:", reply_markup=kb)
                    except TelegramBadRequest:
                        pass
                    await callback.answer()

                    return
                links.append(f"{place}: {deep_link}")

            # Отправляем администратору список ссылок
            if links:
                await callback.message.answer("\n\n".join(links))
            else:
                await callback.answer("Нет доступных мест для генерации ссылок.")


    else:
        await callback.message.edit_text('Ошибка: вы не администратор. Напишите /start - чтобы отправить заявку на администратора')
    await sqlbase.close()

@router_admin_function.callback_query(InlineMainMenu.filter(F.action=="create_QR"))
async def qr(callback: CallbackQuery, state: FSMContext):
    await sqlbase.connect()
    admin_list = await sqlbase.execute_query("""SELECT chat_id FROM admin_list_table""")
    chat_id = callback.message.chat.id
    for admin in admin_list:
        if str(chat_id) == admin[0]:
            places = await sqlbase.execute_query("SELECT place FROM message")
            places = [row[0] for row in places]

            # Генерируем ссылки для каждого места с транслитерацией
            links = []
            for place in places:
                deep_link = await generate_deep_link(sqlbase, place)
                if deep_link is None:
                    kb = await state.get_value("menu_kb")
                    try:
                        await callback.message.edit_text("Добавьте имя бота. Попросите того, у кого есть пароль супер-пользователя,"
                                              " добавить имя бота, отправляющего отзывы.\n\nВыберите действие:", reply_markup=kb)
                    except TelegramBadRequest:
                        pass
                    await callback.answer()
                    return
                links.append(f"{place}: {deep_link}")

            # Отправляем администратору список ссылок
            if links:
                await callback.message.answer("\n\n".join(links))
            else:
                await callback.answer("Нет доступных мест для генерации ссылок.")
                return
            kb_stop = await fabric_keyboard.stop()
            await callback.message.answer(f'Скопируйте ссылку, для которой нужен QR, и отправьте её боту\nСсылки: {"\n\n".join(links)}',
                                          reply_markup=kb_stop)
            await state.set_state(QrR.url)
            return
    else:
        await callback.message.edit_text('Ошибка: вы не администратор. Напишите /start - чтобы отправить заявку на администратора')

@router_admin_function.message(QrR.url, F.text)
async def qr(message: Message, state: FSMContext, callback_data=InlineMainMenu):
    if message.text.lower() == 'стоп':  # Проверяем, завершил ли пользователь процесс
        kb = await fabric_keyboard.inline_main_menu()
        await message.answer("Принудительно завершён процесс создание QR.")
        await message.edit_text("Выберите действие:", reply_markup=kb)
        await state.clear()
    else:
        await state.update_data(url=message.text)
        data = await state.get_data()
        qr_image = qrcode.make(data['url'])
        file_name = f"{uuid4().hex}.png"
        qr_image.save(file_name)

        await message.answer_photo(photo=FSInputFile(file_name), caption=f'Вот ваш QR-код. Нажмите кнопку "Открыть панель действий", чтобы выбрать действий')
        await os.remove(file_name)
        await state.clear()