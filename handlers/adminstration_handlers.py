import base64
import io
import os
import logging
from datetime import datetime, timedelta

import qrcode
import matplotlib.pyplot as plt
from uuid import uuid4
from PIL import Image
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from jobsadd.jobadd import scheduler
from aiogram import Router, F, Bot, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, FSInputFile
from psycopg2 import Error
from db.db import Sqlbase
from dotenv import load_dotenv


logging.basicConfig(level=logging.DEBUG)
load_dotenv()
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


class UpdateAddress(StatesGroup):
    name = State()
    name_state = State()
    adress = State()
    check = State()
    name_place = State()
    messages = State()
    photo = State()


class Address(StatesGroup):
    adress = State()
    check = State()
    name_place = State()
    messages = State()
    photo = State()


class QrR(StatesGroup):
    name = State()
    url = State()


class RemovePA(StatesGroup):
    address = State()
    place = State()


class NameBot(StatesGroup):
    name = State()


class EditMessage(StatesGroup):
    message = State()
    update_message = State()


#Для транскрипции в ссылках

#Кодирование
def encode_data(data):

    return base64.urlsafe_b64encode(data.encode('utf-8')).decode('utf-8')


# Генерация ссылки deep_link для места
async def generate_deep_link(place_name):
    encoded_place = encode_data(place_name)
    # Кодируем место
    bot_username = await sqlbase.execute_query('''SELECT name_bot FROM adm''')
    bot_username = bot_username[0][0]  # Извлекаем имя бота (первый элемент из результата)

    # Если имя бота начинается с '@', убираем только '@'
    if bot_username[0] == '@':
        bot_username = bot_username[1:]

    # Если имя бота заканчивается лишним символом (например, пробелом), удаляем его
    bot_username = bot_username.rstrip()  # Убираем пробелы и символы в конце


    # Предполагаем, что переменная encoded_place определена в другом месте
    return f"https://t.me/{bot_username}?start={encoded_place}"

def reset_base():
    global base
    base = None


#Создание ссылок
async def send_deep_links(message: Message):
        # Получаем список мест из базы
    await sqlbase.connect()
    places = await sqlbase.execute_query("SELECT place FROM message")
    places = [row[0] for row in places]

    # Генерируем ссылки для каждого места с транслитерацией
    links = []
    for place in places:
        deep_link = await generate_deep_link(place)
        links.append(f"{place}: {deep_link}")

    # Отправляем администратору список ссылок
    if links:
        await message.answer("\n\n".join(links))
    else:
        await message.answer("Нет доступных мест для генерации ссылок.")

#Получение мест
async def place_for():
    dictes = {}
    place = await sqlbase.execute_query('SELECT place FROM message')
    for number, names in enumerate(place):
        print(number+1, names[0])
        dictes[number+1] = names[0]
    return dictes

#Получение адресов
async def address_for():
    await sqlbase.connect()

    place = await sqlbase.execute_query('SELECT address FROM message')
    first = {row[0] for row in place}
    return first


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

    await message.answer('*ВНИМАНИЕ*, в аккаунт администратора, может зайти *ТОЛЬКО* один человек\n\nВведите логин:'
                         , parse_mode='MARKDOWN')
    await state.set_state(LoginState.name)


@router.message(LoginState.name, F.text)
async def name(message: Message, state: FSMContext):
    data = await state.get_data()
    namen = data.get("namen")

    if message.text.lower() == 'stop':
        await message.answer('Вход завершён принудительно')
        await state.clear()
        return

    if message.text == namen:
        await message.answer('Логин - правильный.\nВведите пароль:')
        await state.set_state(LoginState.password)
    else:
        await message.answer('Логин не правильный. Введите правильно')


@router.message(LoginState.password, F.text)
async def password(message: Message, state: FSMContext):
    data = await state.get_data()
    passwords = data.get("passwords")

    if message.text == passwords:
        await message.answer('Пароль - правильный\nТеперь у вас права администратора')
        global base
        ids = message.from_user.id
        base = f'{ids}one'
        scheduler.add_job(
            func=reset_base,
            trigger=DateTrigger(run_date=datetime.now() + timedelta(seconds=10))
        )
        scheduler.start()
        await state.clear()
    elif message.text.lower() == 'stop':
        await message.answer('Вход завершён принудительно')
        await state.clear()
    else:
        await message.answer('Пароль - неправильный')

#Добавление админов
@router.message(Command('AddsAdmins'))
async def adds_admins(message: Message, state: FSMContext):
    """Добавление админов"""
    global base
    await sqlbase.connect()
    ids = message.from_user.id
    if base == f'{ids}one':
        await message.answer('Внимание! Заранее подготовьте id пользователей, чтобы их получить. Вы должны прописать '
                             'команду /Userid в этом боте - так вы получите свой id, другие люди должны повторить это действие '
                             'и прислать вам свой id\n'
                             'После, вы добавляете эти Id, даже если они были добавлены до этого.'
                             'Вводите данные по очереди, при этом, если было заполнено 9 админов, но обновили вы 4-ёх, '
                             'то будут обновлены только 4 админа, оставшиеся останутся, '
                             'чтобы их убрать напишите после добавленных id "Нет", чтобы их перезаписать,'
                             ' когда вы всё закончили -'
                             ' напишите "Stop"\n\n'
                             'Имейтe в виду, что максимум 10 пользователей. При этом можно добавить '
                             'нового пользователя, обновить данные, можно только под аккаунтом администратора.')
        scheduler.shutdown()

        await state.set_state(Admins.adm)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')

@router.message(Admins.adm, F.text)
async def add_admin(message: Message, state: FSMContext):
    global base
    if message.text.lower() == 'stop':
        await message.answer("Добавление администраторов завершено.")
        await state.clear()
        await sqlbase.connect()
        rows = await sqlbase.execute_query(
            "SELECT adm_1, adm_2, adm_3, adm_4, adm_5, adm_6, adm_7, adm_8, adm_9, adm_10 FROM adm ORDER BY id DESC LIMIT 1;"
        )

        for count, row in enumerate(rows[0]): #Создание шедулера
            if row not in (None, 'Нет', 'None', 'нет'):
                scheduler.add_job(start_cmd, IntervalTrigger(seconds=60), args=(row, count), id=str(row))

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
        await sqlbase.execute_query(query, params=(message.text.lower(),))

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
    ids = message.from_user.id
    if base == f'{ids}one':
      # Проверяем права
        await message.answer('Введите новый логин')
        await state.set_state(UpdLogin.newlog)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')

@router.message(UpdLogin.newlog, F.text)
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
            base = '0'  # Обновляем переменную состояния
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
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')


@router.message(UpdPassword.newpass, F.text)
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
    ids = message.from_user.id
    if base == f'{ids}one':

        await message.answer('Введите адрес')
        await state.set_state(Address.adress)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')


#Для названия
@router.message(Address.adress, F.text)
async def addres(message: Message, state: FSMContext):
    await state.update_data(addres=message.text)
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс добавление адреса.")
        await state.clear()
    else:
        await message.answer('Введите название')
        await state.set_state(Address.name_place)

#Для сообщения
@router.message(Address.name_place, F.text)
async def name_place(message: Message, state: FSMContext):
    await state.update_data(name_place=message.text)
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс добавление адреса.")
        await state.clear()
    else:
        await message.answer('Введите сообщение к заведению.')
        await state.set_state(Address.messages)



@router.message(Address.messages, F.text)
async def messages(message: Message, state: FSMContext):
    await state.update_data(messages=message.text)
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс добавление адреса.")
        await state.clear()
    else:
        await message.answer('Введите фото(Через ПК - нужна пометка "с сжатием"):')
        await state.set_state(Address.photo)

#Добавление фото
@router.message(UpdateAddress.photo)
@router.message(Address.photo)
async def photos(message: Message, state: FSMContext):
    """Получение фото от адреса"""
    if message.photo:
        update_photo = await state.get_state()
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
        await state.update_data(photos=img_blob)
        if update_photo == 'Update_address:photo':
            data_update = await state.get_data()
            try:
                await sqlbase.execute_query(f'''UPDATE message SET photo = $1 WHERE place = $2''', (data_update['photos'],
                                                                                          data_update['value_data'][0][4], ))
                await message.reply('Фото успешно перезаписано')
            except Exception as e:
                await message.reply(f'Ошибка при добавлении фото: {e}')
            await sqlbase.close()
            if os.path.exists(file_name):
                os.remove(file_name)
            await state.clear()
            return
        else:
            data = await state.get_data()
            await sqlbase.ins(data['addres'], data['messages'], data['photos'], data['name_place'])
            # Уведомление пользователя

            # Удаляем временный файл
            if os.path.exists(file_name):
                os.remove(file_name)
            await message.answer('Адрес и место добавлены')
            # Очищаем состояние
            await state.clear()
    else:
        if message.text.lower() == 'stop':
            await message.answer('Принудительное завершение добавления места')
            await state.clear()
        else:
            await message.answer('Это не фото')

@router.message(Command('EditPlace'))
async def update_place(message: Message, state: FSMContext):
    ids = message.from_user.id
    if base == f'{ids}one':
        await sqlbase.connect()
        n = ""
        mesage = await place_for()
        await state.update_data(local=mesage)
        for i in mesage:
            n += f'{mesage[i]}({i})\n'
        await message.answer(f'Какое место вы хотите изменить. Ниже приведён список мест(Введите цифру):\n{n}')
        await state.set_state(UpdateAddress.name)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')

@router.message(UpdateAddress.name, F.text)
async def update_address_one(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс изменения мест.")
        await state.clear()
        await sqlbase.close()
    else:
        user_number = ''
        data = await state.get_data()
        for nummer in data['local']:
            user_number += str(nummer)

        # Проверка на то существует ли место
        if message.text in user_number:
            value_data = data['local'][int(message.text)]
            await state.update_data(place=value_data)

            # Извлекаем данные из базы данных по адресу
            all_update = await sqlbase.execute_query('''SELECT * FROM message WHERE place = $1 ''', (value_data,))
            await state.update_data(value_data=all_update)
            # Проверяем, что результат существует
            if all_update:
                img_blob = all_update[0][3]

                # Создаём поток из байтов
                image_stream = io.BytesIO(img_blob)
                image_stream.seek(0)

                # Создаём BufferedInputFile (лучше всего для aiogram 3.x)
                photo = types.BufferedInputFile(file=image_stream.read(), filename="image.png")

                # Отправляем
                kb = [
                    [types.KeyboardButton(text='Адрес'), types.KeyboardButton(text='Место')],
                    [types.KeyboardButton(text='Сообщение')],
                    [types.KeyboardButton(text='Фото')],
                ]
                keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True,
                                                     input_field_placeholder='Выберите')
                await bot.send_photo(chat_id=message.from_user.id, caption=f'Это изначальные данные, выберите, что вы'
                                                                           f' хотите изменить:\n'
                                                                           f'Адрес места - {all_update[0][1]}\n'
                                                                           f'Место - {all_update[0][4]}\n'
                                                                           f'Сообщение к нему - {all_update[0][2]}\n'
                                                                           f'Фото приложено', photo=photo, reply_markup=keyboard)


                # Завершаем процесс
                await state.set_state(UpdateAddress.name_state)
        else:
            await message.answer("Этого места не существует")

              # Закрываем соединение с базой данных

@router.message(UpdateAddress.name_state)
async def update_address_too(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс изменения мест.")
        await state.clear()
        await sqlbase.close()
    else:
        if message.text.lower() == 'адрес':
            await message.answer('Введите адрес')
            await state.set_state(UpdateAddress.adress)

        elif message.text.lower() == 'место':
            await message.answer('Введите место')
            await state.set_state(UpdateAddress.name_place)

        elif message.text.lower() == 'сообщение':
            await message.answer('Введите сообщение')
            await state.set_state(UpdateAddress.messages)

        elif message.text.lower() == 'фото':
            await message.answer('Введите фото')
            await state.set_state(UpdateAddress.photo)

@router.message(UpdateAddress.adress, F.text)
async def update_address_for_address(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс изменения мест.")
        await state.clear()
        await sqlbase.close()

    else:
        data = await state.get_data()
        await sqlbase.execute_query(f'''UPDATE message SET address = $1 WHERE place = $2''', (message.text,
                                                                                         data['value_data'][0][4], ))
        await message.answer(f'Успешно обновлён адрес в месте - {data['value_data'][0][4]}')
        await sqlbase.close()

@router.message(UpdateAddress.name_place, F.text)
async def address_name_place(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс изменения мест.")
        await state.clear()
        await sqlbase.close()

    else:
        data = await state.get_data()
        await sqlbase.execute_query(f'''UPDATE message SET place = $1 WHERE place = $2''', (message.text,
                                                                                         data['value_data'][0][4], ))

        await message.answer(f'Успешно обновлёно место в месте - {data['value_data'][0][4]}')
        await sqlbase.close()

@router.message(UpdateAddress.messages, F.text)
async def address_name_for_message(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс изменения мест.")
        await state.clear()
        await sqlbase.close()

    else:
        data = await state.get_data()
        await sqlbase.execute_query(f'''UPDATE message SET message = $1 WHERE place = $2''', (message.text,
                                                                                         data['value_data'][0][4], ))
        await message.answer(f'Успешно обновлёно сообщение в месте - {data['value_data'][0][4]} ')
        await sqlbase.close()

#Удаление места
@router.message(Command('Remove_place'))
async def remove_place(message: Message, state: FSMContext):
    """Удаление мест"""
    ids = message.from_user.id
    if base == f'{ids}one':

        mesage = await place_for()
        variantes = ''
        for nummer in mesage:
            variantes += f'{mesage[nummer]}\n'


        await message.answer(f'*ВНИМАНИЕ! Вы удаляете по конкретному месту, а не по адресу*\nВведите место из списка, приложенного ниже:'
                             f'\nВот все названия заведений:\n{variantes}', parse_mode='Markdown' )
        await state.set_state(RemovePA.place)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')

#Удаление по месту
@router.message(RemovePA.place, F.text)
async def remove_places(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс удаления адресов.")
        await state.clear()
    else:
        await state.update_data(place=message.text)
        try:
            await sqlbase.execute_query('''DELETE FROM message WHERE place = $1 ''', (message.text,))
            await message.answer('Успешно удалено')
            await state.clear()
        except Exception as e:
            await message.answer(f"Произошла ошибка: {str(e)}")

#Удаление по адресу
@router.message(Command('Remove_address'), F.text)
async def remove_place(message: Message, state: FSMContext):
    ids = message.from_user.id
    if base == f'{ids}one':

        await message.answer('*ВНИМАНИЕ! Вы удаляете по конкретному адресу - это означает, что все места '
                             'этим адресом удалятся*\nКакое вы хотите удалить место из приложенного списка мест'
                             '\nВведите место:', parse_mode='Markdown')
        address = await address_for()
        mesage = str(address)
        mesage = mesage.replace('{', '')
        mesage = mesage.replace('}', '')
        mesage = mesage.replace("'", '')
        await message.answer(f'Вот все названия заведений: {mesage}' )
        await state.set_state(RemovePA.address)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')

@router.message(RemovePA.address, F.text)
async def remove_places(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс удаления адресов.")
        await state.clear()
    else:
        await state.update_data(address=message.text)

        await sqlbase.execute_query('''DELETE FROM message WHERE address = $1''', (message.text, ))
        await message.answer('Успешно удалено')
        await state.clear()

#Получение QR-кода
@router.message(Command('Qr'))
async def qr(message: Message, state: FSMContext):
    if base == 'one':
        await message.answer('Напишите название(Возможно любое)')
        await state.set_state(QrR.name)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')


@router.message(QrR.name, F.text)
async def name(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс создания QR.")
        await state.clear()
    else:
        await state.update_data(name=message.text)
        await send_deep_links(message)
        await message.answer('Скопируйте ссылку для которой нужен QR и отправьте её боту')

        await state.set_state(QrR.url)

@router.message(QrR.url, F.text)
async def qr(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс создание QR.")
        await state.clear()
    else:
        await state.update_data(url=message.text)
        data = await state.get_data()
        qr_image = qrcode.make(data['url'])
        file_name = f"{data['name']}.png"
        qr_image.save(file_name)

        await message.answer_photo(photo=FSInputFile(file_name), caption=f"Вот ваш QR для {data['name']}")
        os.remove(file_name)
        await state.clear()

@router.message(Command('Edit_message'))
async def edit_messages(message: Message, state: FSMContext):
    ids = message.from_user.id
    if base == f'{ids}one':
        kb = [[types.KeyboardButton(text='Между оценкой и отзывом')], [types.KeyboardButton(text='После оценки')]]
        keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder='Выберите сообщение')
        await message.answer('Выберите сообщение, которое вы хотите изменить', reply_markup=keyboard)
        await state.set_state(EditMessage.message)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')


@router.message(EditMessage.message)
async def edit_messages_one(message: Message, state: FSMContext):
    await sqlbase.connect()
    if message.text.lower() == 'между оценкой и отзывом':
        await state.update_data(one_message=message.text.lower())
        await state.set_state(EditMessage.update_message)
    elif message.text.lower() == 'после оценки':
        await state.update_data(one_message=message.text.lower())
        await state.set_state(EditMessage.update_message)
    await message.reply('Введите сообщение', reply_markup=types.ReplyKeyboardRemove())

@router.message(EditMessage.update_message)
async def edit_messages_too(message: Message, state: FSMContext):
    await state.update_data(msg=message.text)
    data = await state.get_data()
    if data['one_message'] == 'между оценкой и отзывом':
        await sqlbase.execute_query(
            '''UPDATE static_message SET review_or_rating_message=$1''', (data['msg'], )
        )
        await message.answer('Успешно перезаписано')

    elif data['one_message'] == 'после оценки':
        await sqlbase.execute_query(
            '''UPDATE static_message SET review_message=$1''', (data['msg'], )
        )
        await message.answer('Успешно перезаписано')
    await sqlbase.close()
@router.message(Command('New_name'))
async def new_name(message: Message, state: FSMContext):
    """Обновление имени бота"""
    ids = message.from_user.id
    if base == f'{ids}one':

        await message.answer('Напишите имя бота')
        await state.set_state(NameBot.name)

    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')

@router.message(NameBot.name, F.text)
async def name(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс изменения имени бота.")
        await state.clear()
    else:
        await state.update_data(name=message.text)
        data = await state.get_data()
        await sqlbase.connect()
        await sqlbase.execute_query('''UPDATE adm SET name_bot = $1''', (data['name'],))
        await sqlbase.close()
        await message.answer('Имя перезаписано')

@router.message(Command('Review'))
async def review(message: Message):
    ids = message.from_user.id
    if base == f'{ids}one':


        await sqlbase.connect()


        uuid = uuid4().hex

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

        # Сохраняем график в файл
        file_name = f'{uuid}.png'
        plt.tight_layout()
        plt.savefig(file_name)  # Сохраняем изображение в файл

        photo = FSInputFile(f'{uuid}.png')
        await message.answer_photo(photo)

        # Удаление файла
        os.remove(f'{uuid}.png')

        # Закрытие соединения с БД
        await sqlbase.close()
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')

@router.message(Command(commands=["Generate_links"]))
async def send_deep(message: Message):
    """Генерация чисто ссылок"""
    ids = message.from_user.id
    if base == f'{ids}one':

        await send_deep_links(message)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')


#Для помощи
@router.message(Command('help'))
async def helps(message: Message):
    await message.answer('Команды без использования админских прав:\n'
                         '/StartMessage - запустить отправку сообщений(по умолчанию)\n'
                         '/StopMessage - остановить отправку сообщений\n'
                         '/Login - для входа под ролью администратора(Работать под админом, может только один человек)\n'
                         '/Userid - позволяет любому пользователю узнать свой id\n\n'

                         'Команды с использованием админских прав\n'
                         'Stop - остановка любого процесса(Как сообщение)\n'
                         'Exit - выход из админа, предварительно завершив процесс(Как сообщение)\n'
                         '/UpdLogin - изменить логин\n'
                         '/UpdPassword - изменить пароль\n'
                         '/AddsAdmins - добавить админов\n'
                         '/New_name - изменить имя клиентского бота(нужно для осуществления работы ссылок '
                         'ботов и QR-кодов, работающих на основе ссылок\n'
                         '/Adds_address - добавить новое место\n'
                         '/Remove_address - удалить все места с определённым адресом\n'
                         '/Remove_place - удалить какое-либо место\n'
                         '/Qr - создание QR-кода для заведения\n'
                         '/Review - Посмотреть почасовые средние оценки за 24 часа\n'
                         '/Generate_links - для получения ссылок\n\n'
                         'P.S Отправка уведомлений каждые 60 секунд.'
                         'Не забывайте выключать сообщения во время процесса администрирования\n'
                         'Не забудьте выйти из администратора. Администратор может быть только один. В случае, если'
                         'два человека начнут входить аккаунт администратора, то последний, кто вошёл, и будет '
                         'администратором. Это сделано в целях безопасности.')

@router.message(~F.text)
async def not_f(message: Message):
    await message.answer('Это не текст')