import io

from PIL import Image
from aiofiles import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove

from config import bot
from db.db import Sqlbase
from function.alL_places_or_addresses import place_for, address_for
from keyboard.fabirc_kb import KeyboardFactory

router_for_places = Router()
sqlbase_for_places = Sqlbase()
keyboard_fabric = KeyboardFactory()

class Address(StatesGroup):
    address = State()
    check = State()
    name_place = State()
    messages = State()
    photo = State()


class EditMessage(StatesGroup):
    message = State()
    update_message = State()


class RemovePA(StatesGroup):
    address = State()
    place = State()


class UpdateAddress(StatesGroup):
    name = State()
    name_state = State()
    address = State()
    check = State()
    name_place = State()
    messages = State()
    photo = State()


@router_for_places.message(Command('Adds_address'))
async def start_address(message: Message, state: FSMContext):
    await sqlbase_for_places.connect()
    check_login = await sqlbase_for_places.check_login()
    if check_login:
        await message.answer('Введите адрес')
        await state.set_state(Address.address)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')


#Для названия
@router_for_places.message(Address.address, F.text)
async def addres(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс добавление адреса.")
        await state.clear()
    else:
        await message.answer('Введите название')
        await state.set_state(Address.name_place)

#Для сообщения
@router_for_places.message(Address.name_place, F.text)
async def name_place(message: Message, state: FSMContext):
    await state.update_data(name_place=message.text)
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс добавление адреса.")
        await state.clear()
    else:
        await message.answer('Введите сообщение к заведению.')
        await state.set_state(Address.messages)



@router_for_places.message(Address.messages, F.text)
async def messages(message: Message, state: FSMContext):
    await state.update_data(messages=message.text)
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс добавление адреса.")
        await state.clear()
    else:
        await message.answer('Введите фото(Через ПК - нужна пометка "с сжатием"):')
        await state.set_state(Address.photo)

#Добавление фото
@router_for_places.message(UpdateAddress.photo)
@router_for_places.message(Address.photo)
async def photos(message: Message, state: FSMContext):
    """Получение фото от адреса"""
    update_photo = await state.get_state()
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
        await state.update_data(photos=img_blob)
        if update_photo == 'UpdateAddress:photo':
            data_update = await state.get_data()
            try:
                await sqlbase_for_places.execute_query(f'''UPDATE message SET photo = $1 WHERE place = $2''', (data_update['photos'],
                                                                                                               data_update['value_data'][0][4],))
                await message.reply('Фото успешно перезаписано')
            except Exception as e:
                await message.reply(f'Ошибка при добавлении фото: {e}')
            await sqlbase_for_places.close()
            if os.path.exists(file_name):
                await os.remove(file_name)
            await state.clear()
            return
        else:
            data = await state.get_data()
            await sqlbase_for_places.insert_message(data['addres'], data['messages'], data['photos'], data['name_place'])
            # Уведомление пользователя

            # Удаляем временный файл
            if os.path.exists(file_name):
                await os.remove(file_name)
            await message.answer('Адрес и место добавлены')
            # Очищаем состояние
            await state.clear()
    else:
        if update_photo == 'UpdateAddress:photo':
            if message.text.lower() == 'stop':
                await message.answer('Принудительное завершение изменения места')
                await state.clear()
            else:
                await message.answer('Это не фото')
        else:
            if message.text.lower() == 'stop':
                await message.answer('Принудительное завершение добавления места')
                await state.clear()
            else:
                await message.answer('Это не фото')

@router_for_places.message(Command('Edit_message'))
async def edit_messages(message: Message, state: FSMContext):
    await sqlbase_for_places.connect()
    check_login = await sqlbase_for_places.check_login()
    if check_login:

        keyboard = await keyboard_fabric.builder_choice()
        await message.answer('Выберите сообщение, которое вы хотите изменить', reply_markup=keyboard)
        await state.set_state(EditMessage.message)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')


@router_for_places.message(EditMessage.message)
async def edit_messages_one(message: Message, state: FSMContext):
    await sqlbase_for_places.connect()
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await state.clear()
        await sqlbase_for_places.close()
        await message.answer("Принудительно завершён процесс изменения сообщений для клиентского бота.")
        return
    if message.text.lower() == 'между оценкой и отзывом':
        await state.update_data(one_message=message.text.lower())
        await state.set_state(EditMessage.update_message)
    elif message.text.lower() == 'после оценки':
        await state.update_data(one_message=message.text.lower())
        await state.set_state(EditMessage.update_message)
    await message.reply('Введите сообщение', reply_markup=ReplyKeyboardRemove())

@router_for_places.message(EditMessage.update_message)
async def edit_messages_too(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await state.clear()
        await sqlbase_for_places.close()
        await message.answer("Принудительно завершён процесс изменения сообщений для клиентского бота.")
        return
    await state.update_data(msg=message.text)
    data = await state.get_data()
    if data['one_message'] == 'между оценкой и отзывом':

        await sqlbase_for_places.execute_query(
            '''UPDATE static_message SET review_or_rating_message=$1 WHERE id = 1''', (data['msg'], )
        )
        await message.answer('Успешно перезаписано')

    elif data['one_message'] == 'после оценки':
        await sqlbase_for_places.execute_query(
            '''UPDATE static_message SET review_message=$1 WHERE id = 1''', (data['msg'], )
        )
        await message.answer('Успешно перезаписано')
    await sqlbase_for_places.close()

#Удаление места
@router_for_places.message(Command('Remove_place'))
async def remove_place(message: Message, state: FSMContext):
    """Удаление мест"""
    await sqlbase_for_places.connect()
    check_login = await sqlbase_for_places.check_login()
    if check_login:
        places = await place_for(sqlbase_for_places)
        variantes = ''
        for nummer in places:
            variantes += f'{places[nummer]}\n'

        await message.answer(f'*ВНИМАНИЕ! Вы удаляете по конкретному месту, а не по адресу*\nВведите место из списка, приложенного ниже:'
                             f'\nВот все названия заведений:\n{variantes}', parse_mode='Markdown' )
        await state.set_state(RemovePA.place)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')

#Удаление по месту
@router_for_places.message(RemovePA.place, F.text)
async def remove_places(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс удаления адресов.")
        await state.clear()
    else:
        await state.update_data(place=message.text)
        try:
            await sqlbase_for_places.execute_query('''DELETE FROM message WHERE place = $1 ''', (message.text,))
            await message.answer('Успешно удалено')
            await state.clear()
        except Exception as e:
            await message.answer(f"Произошла ошибка: {str(e)}")
    await sqlbase_for_places.close()


#Удаление по адресу
@router_for_places.message(Command('Remove_address'), F.text)
async def remove_place(message: Message, state: FSMContext):
    await sqlbase_for_places.connect()
    check_login = await sqlbase_for_places.check_login()
    if check_login:

        await message.answer('*ВНИМАНИЕ! Вы удаляете по конкретному адресу - это означает, что все места '
                             'этим адресом удалятся*\nКакое вы хотите удалить место из приложенного списка мест'
                             '\nВведите место:', parse_mode='Markdown')
        address = await address_for(sqlbase_for_places)

        true_message = str(address)
        true_message = true_message.replace('{', '')
        true_message = true_message.replace('}', '')
        true_message = true_message.replace("'", '')

        await message.answer(f'Вот все названия заведений: {true_message}')
        await state.set_state(RemovePA.address)
    else:
        await message.answer('Ошибка: вы не администратор. Напишите /Login - чтобы начать процесс входа в аккаунт '
                             'администратора')

@router_for_places.message(RemovePA.address, F.text)
async def remove_places(message: Message, state: FSMContext):
    if message.text.lower() == 'stop':  # Проверяем, завершил ли пользователь процесс
        await message.answer("Принудительно завершён процесс удаления адресов.")
        await state.clear()
    else:
        await state.update_data(address=message.text)

        await sqlbase_for_places.execute_query('''DELETE FROM message WHERE address = $1''', (message.text,))
        await message.answer('Успешно удалено')
        await state.clear()
    await sqlbase_for_places.close()