import base64
import os
import io
import logging
from uuid import uuid4

from PIL import Image
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from transliterate import translit
import qrcode
from jobsadd.jobadd import scheduler
import matplotlib.pyplot as plt
from aiogram import Router, F, Bot, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, FSInputFile, InputFile
from psycopg2 import Error
from db.db import Sqlbase
# from dotenv import load_dotenv

from handlers.starts import start_cmd

logging.basicConfig(level=logging.DEBUG)
# load_dotenv()
sqlbase = Sqlbase()

base = None
router = Router()
bot = Bot(token=os.getenv('API_KEY'), parce_mode='MARKDOWN')

class UpdLogin(StatesGroup):
    newlog = State()


class UpdPassword(StatesGroup):
    newpass = State()


class Admins(StatesGroup):
    adm = State()


class LoginState(StatesGroup):
    name = State()
    password = State()


class Address(StatesGroup):
    adress = State()
    check = State()
    name_place = State()
    messages = State()
    photo = State()

class Qr_r(StatesGroup):
    name = State()
    url = State()

class remove_p_a(StatesGroup):
    address = State()
    place = State()

class Name_bot(StatesGroup):
    name = State()


#Для транскрипции в ссылках
def transliterate_text(text):
    return translit(text, language_code='ru', reversed=True)

#Кодирование
def encode_data(data):
    return base64.urlsafe_b64encode(data.encode()).decode()

# Функция декодирования для deep_link
def decode_data(payload):
    try:
        return base64.urlsafe_b64decode(payload.encode()).decode()
    except Exception:
        return None


# Генерация ссылки deep_link для места
async def generate_deep_link(place_name):
    transliterated_name = transliterate_text(place_name)  # Транслитерируем место
    print(transliterated_name)
    encoded_place = encode_data(transliterated_name)
    # Кодируем место
    bot_username = await sqlbase.execute_query('''SELECT name_bot FROM adm''')
    bot_username = bot_username[0][0]  # Извлекаем имя бота (первый элемент из результата)

    # Если имя бота начинается с '@', убираем только '@'
    if bot_username[0] == '@':
        bot_username = bot_username[1:]

    # Если имя бота заканчивается лишним символом (например, пробелом), удаляем его
    bot_username = bot_username.rstrip()  # Убираем пробелы и символы в конце

    print(bot_username)  # Выводим очищенное имя бота

    # Предполагаем, что переменная encoded_place определена в другом месте
    return f"https://t.me/{bot_username}?start={encoded_place}"


#Создание ссылок
async def send_deep_links(message: Message):
        # Получаем список мест из базы
    await sqlbase.connect()
    places = await sqlbase.execute_query("SELECT place FROM message")
    places = [row[0] for row in places]

    # Генерируем ссылки для каждого места с транслитерацией
    links = []
    for place in places:
        print(place)
        deep_link = await generate_deep_link(place)
        links.append(f"{place}: {deep_link}")

    # Отправляем администратору список ссылок
    if links:
        await message.answer("\n\n".join(links))
    else:
        await message.answer("Нет доступных мест для генерации ссылок.")

#Получение мест
async def place_for(message: Message):
    await sqlbase.connect()

    place = await sqlbase.execute_query('SELECT place FROM message')
    first = {row[0] for row in place}
    return first

#Получение адресов
async def address_for(message: Message):
    await sqlbase.connect()

    place = await sqlbase.execute_query('SELECT address FROM message')
    first = {row[0] for row in place}
    return first

#Для остановки ЛЮБЫХ процессов

#Для выхода из админа
@router.message(F.text.lower() == 'exit')
async def handle_stop(message: Message, state: FSMContext):
    await message.answer("Вы вышли из админа")
    global base
    base = None
    await sqlbase.close()
    await state.clear()

#Для логина
@router.message(Command('Login'))
async def login(message: Message, state: FSMContext):
    await sqlbase.connect()
    # Выполнение запроса для получения имени и пароля
    names = await sqlbase.execute_query('SELECT name, password FROM adm')

    if not names:
        await message.answer("Ошибка: данные для входа не найдены.")
        return

    # Сохранение имени и пароля в контексте FSM
    namen, passwords = names[0]
    await state.update_data(namen=namen, passwords=passwords)

    await message.answer('Введите логин:')
    await state.set_state(LoginState.name)


@router.message(LoginState.name)
async def name(message: Message, state: FSMContext):
    data = await state.get_data()
    namen = data.get("namen")

    if message.text.lower() == 'stop':
        await message.answer('Вход завершён принудительно')
        await state.clear()
        return

    if message.text == namen:
        await message.answer('Имя - правильное\nВведите пароль:')
        await state.set_state(LoginState.password)
    else:
        await message.answer('Имя не правильное. Введите правильно')


@router.message(LoginState.password)
async def password(message: Message, state: FSMContext):
    data = await state.get_data()
    passwords = data.get("passwords")

    if message.text == passwords:
        await message.answer('Пароль - правильный\nТеперь у вас права администратора')
        global base
        base = 'one'
        await state.clear()
    elif message.text.lower() == 'stop':
        await message.answer('Вход завершён принудительно')
        await state.clear()
    else:
        await message.answer('Пароль - неправильный')

#Добавление админов
@router.message(Command('AddsAdmins'))
async def AddsAdmins(message: Message, state: FSMContext):
    """Добалвние админов"""
    global base
    await sqlbase.connect()

    if base == 'one':
        await message.answer('Внимание! Заранее подготовьте id пользователей, чтобы их найти, вы должны зайти в продвинутые '
                             'Настройки -> Продвинутые настройки -> Экспериментальные настройки -> '
                             'И включить Show Peer IDs in Profile, после в каждом профиле есть id, вы должны вставить свой '
                             'id и других, даже если они были до этого. Вводите данные очерёдностью, как только вы ввели все данные'
                             'напишите "Stop"\n\n'
                             'Имейтe в виду, что максимум 10 пользователей. При этом можно добавить '
                             'нового пользователя, обновить данные, можно только под логином и паролем админа.')
        scheduler.shutdown()

        await state.set_state(Admins.adm)
    else:
        await message.answer('Вы не под администратором')

@router.message(Admins.adm)
async def AddAdmin(message: Message, state: FSMContext):
    global base
    if message.text.lower() == 'stop':
        await message.answer("Добавление администраторов завершено.")
        await state.clear()
        base = 'Too'
        await sqlbase.connect()
        rows = await sqlbase.execute_query(
            "SELECT adm_1, adm_2, adm_3, adm_4, adm_5, adm_6, adm_7, adm_8, adm_9, adm_10 FROM adm ORDER BY id DESC LIMIT 1;"
        )

        for count, row in enumerate(rows[0]): #Создание шедулера
            if row not in (None, 'Нет', 'None', 'нет'):
                scheduler.add_job(start_cmd, IntervalTrigger(seconds=5), args=(row, count), id=str(row))

        # Стартуем шедулер, задача будет активна по умолчанию
        scheduler.start()
        return

        # Получаем текущие данные из состояния
    data = await state.get_data()

    # Проверяем, сколько ID уже добавлено
    current_count = data.get('current_count', 0)

    if current_count >= 10:
        await message.answer("Вы добавили максимум администраторов (10). Завершите процесс командой 'Stop'.")
        return

    # Формируем имя столбца (adm_1, adm_2 и т.д.)
    column_name = f"adm_{current_count + 1}"

    # Обновляем базу данных
    try:
        query = f"UPDATE adm SET {column_name} = $1 WHERE id = 1;"
        await sqlbase.execute_query(query, params=(message.text,))

        # Обновляем состояние
        await state.update_data(current_count=current_count + 1)

        await message.answer(f"ID добавлен в {column_name}. Введите следующий ID или напишите 'Stop'.")
    except Error as e:
        await message.answer(f"Произошла ошибка: {str(e)}")

#Изменение логина
@router.message(Command('UpdLogin'))
async def upd(message: Message, state: FSMContext):
    """Обновление логина"""
    global base
    if base == 'one':  # Проверяем права
        await message.answer('Введите новый логин')
        await state.set_state(UpdLogin.newlog)
    else:
        await message.answer('Вы не под администратором')

@router.message(UpdLogin.newlog)
async def newlogs(message: Message, state: FSMContext):
    # Получаем данные из состояния
    data = await state.get_data()
    altnewlog = data.get("altnewlog")  # Первый ввод логина

    if altnewlog is None:  # Первый ввод нового логинае п
        if message.text.lower() == 'stop':
            await message.answer("Обновление логина прервано.")
            await state.clear()
        else:
            await state.update_data(altnewlog=message.text)
            await message.answer('Введите ещё раз новый логин для подтверждения.')
    else:  # Второй ввод логина
        if message.text.lower() == 'stop':
            await message.answer("Обновление логина прервано.")
            await state.clear()
        elif altnewlog == message.text:  # Если логины совпадают
            query = 'UPDATE adm SET name = $1 WHERE id = 1;'
            await sqlbase.execute_query(query, params=(altnewlog,))
            await message.answer('Логин успешно обновлён!')
            global base
            base = 'too'  # Обновляем переменную состояния
            await state.clear()
        else:  # Если логины не совпадают
            await message.answer('Логины не совпадают. Повторите ввод нового логина.')
            await state.update_data(altnewlog=None)  # Сбрасываем первый ввод

#Изменение пароля
@router.message(Command('UpdPassword'))
async def upd(message: Message, state: FSMContext):
    """Изменение пароля"""
    if base == 'one':
        await message.answer('Введите новый пароль')
        await state.set_state(UpdPassword.newpass)
    else:
        await message.answer('Вы не под администратором')


@router.message(UpdPassword.newpass)
async def new_password(message: Message, state: FSMContext):
    """Изменение пароля"""
    global base

    data = await state.get_data()
    altnewpass = data.get("altnewpass")  # Проверяем, был ли сохранён первый ввод пароля

    if altnewpass is None:  # Первый ввод пароля
        if message.text.lower() == 'stop':
            await message.answer("Обновление пароля прервано.")
            await state.clear()
        else:
            await state.update_data(altnewpass=message.text)  # Сохраняем первый ввод
            await message.answer('Введите ещё раз новый пароль, чтобы подтвердить.')
    else:  # Второй ввод пароля
        if message.text.lower() == 'stop':
            await message.answer("Обновление пароля прервано.")
            await state.clear()
        elif altnewpass == message.text: #При совпадении пароля
            query = 'UPDATE adm SET password = $1 WHERE id = 1;'
            await sqlbase.execute_query(query, params=(altnewpass,))
            await message.answer('Пароль успешно обновлён!')
            base = 'too'
            await state.clear()
        else:  # Если пароли не совпадают
            await message.answer('Пароли не совпадают. Повторите ввод нового пароля.')
            await state.set_state(UpdPassword.newpass)  # Возвращаем в текущее состояние

#Добавление адресов
@router.message(Command('Adds_address'))
async def start_addres(message: Message, state: FSMContext):
    global base
    if base == 'one':
        await message.answer('Введите адрес')
        if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
            await message.answer("Принудительно завершён процесс добавление адреса.")
            await state.clear()
        await state.set_state(Address.adress)
    else:
        await message.answer('Вы не под администратором')


#Для названия
@router.message(Address.adress, F.text)
async def addres(message: Message, state: FSMContext):
    await state.update_data(addres=message.text)
    await message.answer('Введите название')
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс добавление адреса.")
        await state.clear()
    await state.set_state(Address.name_place)

#Для сообщения
@router.message(Address.name_place, F.text)
async def name_place(message: Message, state: FSMContext):
    await state.update_data(name_place=message.text)
    await message.answer('Введите сообщение к заведению.')
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс добавление адреса.")
        await state.clear()
    await state.set_state(Address.messages)


@router.message(Address.messages, F.text)
async def messages(message: Message, state: FSMContext):
    await state.update_data(messages=message.text)
    await message.answer('Введите фото(Через ПК - нужна пометка "с сжатием"):')
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс добавление адреса.")
        await state.clear()
    await state.set_state(Address.photo)

#Добавление фото
@router.message(Address.photo)
async def photos(message: Message, state: FSMContext):
    """Получение фото от адреса"""
    if message.photo:
        photo = message.photo[-1]  # Берем фото в наилучшем качестве
        file_info = await bot.get_file(photo.file_id)  # Получаем информацию о файле
        file_path = file_info.file_path  # Путь к файлу на серверах Telegram
        file_name = f"{photo.file_id}.jpeg"  # Задаем имя файла

        # Скачиваем файл
        await bot.download_file(file_path, destination=file_name)


        # Открываем и сжимаем изображение
        image = Image.open(file_name)
        image = image.convert("RGB")  # Преобразуем в RGB, если изображение имеет альфа-канал
        img_byte_arr = io.BytesIO()  # Создаем поток в памяти
        image.save(img_byte_arr, format="JPEG", quality=80, optimize=True)  # Сохраняем сжато в поток

        # Преобразуем в BLOB
        img_blob = img_byte_arr.getvalue()

        # Сохраняем blob в состояние FSM
        await state.update_data(photos=img_blob)
        data = await state.get_data()

        # Сохраняем данные в базу
        await sqlbase.ins(data['addres'], data['messages'], data['photos'], data['name_place'], transliterate_text(data['name_place']))
        # Уведомление пользователя

        # Удаляем временный файл
        if os.path.exists(file_name):
            os.remove(file_name)
        await message.answer('Адрес и место добавлены')
        # Очищаем состояние
        await state.clear()
    else:
        await message.answer('Это не фото')

#Удаление места
@router.message(Command('Remove_place'))
async def remove_place(message: Message, state: FSMContext):
    """Удаление мест"""
    if base == 'one':
        if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
            await message.answer("Принудительно завершён процесс удаления мест.")
            await state.clear()
        await message.answer('*ВНИМАНИЕ! Вы удаляете по конкретному месту, а не по адресу*\nА также приложен список мест'
                             '\nВведите место:', parse_mode='Markdown')
        mesage = await place_for(message)
        mesage = str(mesage)
        #Убираем лишние знаки
        mesage = mesage.replace('{', '')
        mesage = mesage.replace('}', '')
        mesage = mesage.replace("'", '')

        await message.answer(f'Вот все названия заведений: {mesage}' )
        await state.set_state(remove_p_a.place)
    else:
        await message.answer('Вы не под администратором')

#Удаление по месту
@router.message(remove_p_a.place)
async def remove_places(message: Message, state: FSMContext):

    await state.update_data(place=message.text)
    try:
        await sqlbase.execute_query('''DELETE FROM message WHERE place = $1 ''', (message.text,))
        await message.answer('Успешно удалено')
        await state.clear()

    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")

#Удаление по адресу
@router.message(Command('Remove_address'))
async def remove_place(message: Message, state: FSMContext):
    if base == 'one':
        if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
            await message.answer("Принудительно завершён процесс удаления адресов.")
            await state.clear()
        await message.answer('*ВНИМАНИЕ! Вы удаляете по конкретному адресу - это означает, что все места этим адресом удалятся*\nА также приложен список мест'
                             '\nВведите место:', parse_mode='Markdown')
        address = await address_for(message)
        mesage = str(address)
        mesage = mesage.replace('{', '')
        mesage = mesage.replace('}', '')
        mesage = mesage.replace("'", '')
        await message.answer(f'Вот все названия заведений: {mesage}' )
        await state.set_state(remove_p_a.address)
    else:
        await message.answer('Вы не под администратором')

@router.message(remove_p_a.address)
async def remove_places(message: Message, state: FSMContext):

    await state.update_data(address=message.text)

    await sqlbase.execute_query('''DELETE FROM message WHERE address = $1''', (message.text, ))
    await message.answer('Успешно удалено')
    await state.clear()

#Получение QR-кода
@router.message(Command('Qr'))
async def qr(message: Message, state: FSMContext):
    if base == 'one':
        if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
            await message.answer("Принудительно завершён процесс создания QR.")
            await state.clear()
        await message.answer('Напишите название(Возможно любое)')
        await state.set_state(Qr_r.name)
    else:
        await message.answer('Вы не под администратором')


@router.message(Qr_r.name)
async def name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await send_deep_links(message)
    await message.answer('Скопируйте ссылку для которой нужен QR и отправьте её боту')
    if message.text.lower() == 'Stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс создания QR.")
        await state.clear()
    await state.set_state(Qr_r.url)

@router.message(Qr_r.url)
async def qr(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс создание QR.")
        await state.clear()
    await state.update_data(url=message.text)
    data = await state.get_data()
    qr_image = qrcode.make(data['url'])
    file_name = f"{data['name']}.png"
    qr_image.save(file_name)

    await message.answer_photo(photo=FSInputFile(file_name), caption=f"Вот ваш QR для {data['name']}")
    os.remove(file_name)
    await state.clear()

@router.message(Command('New_name'))
async def review(message: Message, state: FSMContext):
    """Обновление имени бота"""
    if base == 'one':
        await message.answer('Напишите имя бота')
        await state.set_state(Name_bot.name)
        if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
            await message.answer("Принудительно завершён процесс изменения имени.")
            await state.clear()
    else:
        await message.answer('Вы не под администратором')

@router.message(Name_bot.name)
async def name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    data = await state.get_data()
    await sqlbase.connect()
    await sqlbase.execute_query('''UPDATE adm SET name_bot = $1''', (data['name'],))
    await sqlbase.close()
    await message.answer('Имя перезаписано')

import os
import matplotlib.pyplot as plt
from uuid import uuid4

@router.message(Command('review'))
async def review(message: Message):
    await sqlbase.connect()

    # Генерация уникального идентификатора для файла
    uuid = uuid4().hex  # Преобразуем UUID в строку для использования в имени файла

    # Запрос к БД для получения данных
    data = await sqlbase.execute_query("""
        SELECT 
            DATE_TRUNC('hour', data_times::TIMESTAMP) AS hour,
            AVG(rating) AS average_rating
        FROM servers
        WHERE data_times::TIMESTAMP >= NOW() - INTERVAL '24 hours'
        GROUP BY hour
        ORDER BY hour;
    """)

    # Обработка данных
    hours = [row['hour'] for row in data]
    avg_ratings = [row['average_rating'] for row in data]

    plt.figure(figsize=(10, 6))
    plt.bar(hours, avg_ratings, width=0.03)  # Уменьшаем ширину столбцов


    # Настраиваем оси и подписи
    plt.xlabel('Дата')
    plt.ylabel('Оценка')
    plt.title('Средняя оценка по часам за последние 24 часа')
    plt.xticks(rotation=45)
    # Сохраняем график в файл
    file_name = f'{uuid}.png'
    plt.tight_layout()
    plt.savefig(file_name)  # Сохраняем изображение в файл
    photo = FSInputFile(f'{uuid}.png')
    await message.answer_photo(photo)
    # Получаем ID пользователя
    os.remove(f'{uuid}.png')
    # Закрытие соединения с БД
    await sqlbase.close()

@router.message(Command(commands=["Generate_links"]))
async def send_deep(message: Message):
    """Генерация чисто ссылок"""
    if base == 'one':
        await send_deep_links(message)
    else:
        await message.answer('Вы не под администратором')


#Для помощи
@router.message(Command('help'))
async def help(message: Message):
    await message.answer('Команды без использования админских прав:\n'
                         '/StartMessage - Запустить отправку сообщений(по умолчанию)\n'
                         '/StopMessage - Остановить отправку сообщений\n\n'
                         'Команды с использованием админских прав\n'
                         '/Login - для входа под ролью администратора(Работать под админом, может только один человек)\n'
                         'Stop - остановка любого процесса(Как сообщение)\n'
                         'Exit - выход из админа, предварительно завершив процесс(Как сообщение)\n'
                         '/UpdLogin - изменить логин\n'
                         '/UpdPassword - изменить пароль\n'
                         '/AddsAdmins - добавить админов\n'
                         '/New_name - Изменить имя клиентского бота(нужно для осуществления работы ссылок ботов и QR-кодов, работающих на основе ссылок\n'
                         '/Adds_address - добавить новое место\n'
                         '/Remove_address - удалить все места с определённым адресом\n'
                         '/Remove_place - удалить какое-либо место\n'
                         '/Remove_place - удалить какое-либо место\n'
                         '/Qr - создание QR-кода для заведений\n'
                         '/Generate_links - для получения ссылок\n\n'
                         'P.S Отправка уведомлений каждые 60 секунд.'
                         'Не забывайте выключать сообщения во время процесса администрирования\n'
                         'Не забудьте выйти из администратора.')
