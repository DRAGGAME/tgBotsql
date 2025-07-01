from uuid import uuid4

import qrcode
from aiofiles import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, FSInputFile
from apscheduler.triggers.interval import IntervalTrigger
from matplotlib import pyplot as plt

from db.db import Sqlbase
from function.generate_link import generate_deep_link
from schedulers.scheduler_object import scheduler
from schedulers.starts import start_cmd

router_for_admin_function = Router()
sqlbase_admin_function = Sqlbase()


class QrR(StatesGroup):
    name = State()
    url = State()


class NameBot(StatesGroup):
    name = State()


@router_for_admin_function.message(Command('StartMessage'))
async def start_message(message: Message):
    """
    Начать пересылку сообщений
    :param message:
    """
    chat_id = message.chat.id
    job = scheduler.get_job(str(chat_id))
    await sqlbase_admin_function.connect()
    admin_list = await sqlbase_admin_function.execute_query("""SELECT chat_id FROM admin_list_table""")
    if chat_id in admin_list:
        if not job:
            scheduler.add_job(start_cmd, IntervalTrigger(seconds=60), id=str(chat_id))

        scheduler.resume_job(str(chat_id))
    await message.answer('Теперь сообщения будут доставляться вам')


@router_for_admin_function.message(Command('StopMessage'))
async def stop_message(message: Message):
    """
    Остановить пересылку сообщений
    :param message:
    """
    chat_id = message.chat.id

    job = scheduler.get_job(str(chat_id))
    admin_list = await sqlbase_admin_function.execute_query("""SELECT chat_id FROM admin_list_table""")

    if chat_id in admin_list:

        if job:
            # Останавливаем задачу, если она существует
            scheduler.pause_job(str(chat_id))
            await message.answer('Теперь сообщения не доставляются вам')
    else:
        await message.answer('Вас нет в списке администраторов')


@router_for_admin_function.message(Command('Qr'))
async def qr(message: Message, state: FSMContext):
    await sqlbase_admin_function.connect()
    check_login = await sqlbase_admin_function.check_login()
    if check_login:
        await message.answer('Скопируйте ссылку для которой нужен QR и отправьте её боту')
        await state.set_state(QrR.url)
        await state.set_state(QrR.name)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')


@router_for_admin_function.message(QrR.url, F.text)
async def qr(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс создание QR.")
        await state.clear()
    else:
        await state.update_data(url=message.text)
        data = await state.get_data()
        qr_image = qrcode.make(data['url'])
        file_name = f"{uuid4().hex}.png"
        qr_image.save(file_name)

        await message.answer_photo(photo=FSInputFile(file_name), caption=f"Вот ваш QR для {data['name']}")
        await os.remove(file_name)
        await state.clear()


@router_for_admin_function.message(Command('New_name'))
async def new_name(message: Message, state: FSMContext):
    """Обновление имени бота"""
    await sqlbase_admin_function.connect()
    check_login = await sqlbase_admin_function.check_login()
    if check_login:

        await message.answer('Напишите имя бота')
        await state.set_state(NameBot.name)

    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')

@router_for_admin_function.message(NameBot.name, F.text)
async def name(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс изменения имени клиентского бота.")
        await state.clear()
    else:
        await state.update_data(name=message.text)
        data = await state.get_data()
        await sqlbase_admin_function.connect()
        await sqlbase_admin_function.execute_query('''UPDATE adm SET name_bot = $1''', (data['name'],))
        await sqlbase_admin_function.close()
        await message.answer('Имя перезаписано')

@router_for_admin_function.message(Command('Review'))
async def review(message: Message):
    await sqlbase_admin_function.connect()
    check_login = await sqlbase_admin_function.check_login()
    if check_login:
        uuid = uuid4().hex

        data = await sqlbase_admin_function.execute_query("""
            SELECT 
                DATE_TRUNC('hour', data_times::TIMESTAMP) AS hour,
                AVG(rating) AS average_rating
            FROM servers
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
            await message.answer_photo(photo)

            # Удаление файла
            await os.remove(f'{uuid}.png')
        else:
            await message.answer('Нет данных по оценкам за 24 часа')
        await sqlbase_admin_function.close()
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')

@router_for_admin_function.message(Command(commands=["Generate_links"]))
async def send_deep(message: Message):
    """Генерация чисто ссылок"""
    await sqlbase_admin_function.connect()
    check_login = await sqlbase_admin_function.check_login()
    if check_login:
        await sqlbase_admin_function.connect()
        places = await sqlbase_admin_function.execute_query("SELECT place FROM message")
        places = [row[0] for row in places]

        # Генерируем ссылки для каждого места с транслитерацией
        links = []
        for place in places:
            deep_link = await generate_deep_link(sqlbase_admin_function, place)
            links.append(f"{place}: {deep_link}")

        # Отправляем администратору список ссылок
        if links:
            await message.answer("\n\n".join(links))
        else:
            await message.answer("Нет доступных мест для генерации ссылок.")
        await sqlbase_admin_function.close()

    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')