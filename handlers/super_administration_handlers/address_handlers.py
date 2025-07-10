import io

from PIL import Image
from aiofiles import os
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, BufferedInputFile

from config import bot
from db.db import Sqlbase
from function.alL_places_or_addresses import place_for, address_for
from keyboard.menu_fabric import InlineMainMenu, FabricInline

router_for_places = Router()
sqlbase_for_places = Sqlbase()
keyboard_fabric = FabricInline()


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


@router_for_places.callback_query(InlineMainMenu.filter(F.action == "add_place"))
async def start_address(callback: CallbackQuery, state: FSMContext):
    await sqlbase_for_places.connect()
    check_login = await sqlbase_for_places.check_login()
    if check_login:
        admin_kb = await keyboard_fabric.inline_admin_main_menu()
        await state.update_data(admin_kb=admin_kb)
        kb = await keyboard_fabric.stop()
        await callback.message.answer('Введите адрес', reply_markup=kb)
        await callback.answer()
        await state.set_state(Address.address)
    else:
        await callback.answer('Вы не супер-администратор, у вас нет этой функции')


# Для названия
@router_for_places.message(Address.address, F.text)
async def input_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer('Введите название')
    await state.set_state(Address.name_place)


# Для сообщения
@router_for_places.message(Address.name_place, F.text)
async def name_place(message: Message, state: FSMContext):
    await state.update_data(name_place=message.text)

    await message.answer('Введите сообщение к заведению.')
    await state.set_state(Address.messages)


@router_for_places.message(Address.messages, F.text)
async def messages(message: Message, state: FSMContext):
    await state.update_data(messages=message.text)

    await message.answer('Введите фото(Через ПК - нужна пометка "с сжатием"):')
    await state.set_state(Address.photo)


# Добавление фото
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
                await sqlbase_for_places.execute_query(f'''UPDATE message SET photo = $1 WHERE place = $2''',
                                                       (data_update['photos'],
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
            await sqlbase_for_places.insert_message(data['address'], data['messages'], data['photos'],
                                                    data['name_place'])
            # Уведомление пользователя

            # Удаляем временный файл
            if os.path.exists(file_name):
                await os.remove(file_name)
            await message.answer('Адрес и место добавлены')
            # Очищаем состояние
            await state.clear()
    else:
        await message.answer("Это не фото")


@router_for_places.callback_query(InlineMainMenu.filter(F.action == "edit_messages"))
async def edit_messages(callback: CallbackQuery, state: FSMContext):
    await sqlbase_for_places.connect()
    check_login = await sqlbase_for_places.check_login()
    if check_login:

        keyboard = await keyboard_fabric.builder_choice()
        await callback.message.answer('Выберите сообщение, которое вы хотите изменить', reply_markup=keyboard)
        await callback.answer()
        await state.set_state(EditMessage.message)
    else:
        await callback.answer('Вы не супер-администратор, у вас нет этой функции')


@router_for_places.message(EditMessage.message)
async def edit_messages_one(message: Message, state: FSMContext):
    await sqlbase_for_places.connect()

    if message.text.lower() == 'между оценкой и отзывом':
        await state.update_data(one_message=message.text.lower())
        await state.set_state(EditMessage.update_message)
    elif message.text.lower() == 'после оценки':
        await state.update_data(one_message=message.text.lower())
        await state.set_state(EditMessage.update_message)
    await message.reply('Введите сообщение')


@router_for_places.message(EditMessage.update_message)
async def edit_messages_too(message: Message, state: FSMContext):
    await state.update_data(msg=message.text)
    data = await state.get_data()
    try:
        kb = await keyboard_fabric.inline_admin_main_menu()

        if data['one_message'] == 'между оценкой и отзывом':

            await sqlbase_for_places.execute_query(
                '''UPDATE settings_for_review_bot SET review_or_rating_message=$1 WHERE id = 1''', (data['msg'],)
            )

        elif data['one_message'] == 'после оценки':
            await sqlbase_for_places.execute_query(
                '''UPDATE settings_for_review_bot SET review_message=$1 WHERE id = 1''', (data['msg'],)
            )
        await message.answer('Успешно перезаписано\nВыберите действие', reply_markup=kb)
    except Exception:
        pass
    await sqlbase_for_places.close()


# Удаление по месту
@router_for_places.message(RemovePA.place, F.text)
async def remove_places(message: Message, state: FSMContext):
    await state.update_data(place=message.text)
    try:
        await sqlbase_for_places.execute_query('''DELETE FROM message WHERE place = $1 ''', (message.text,))
        await message.answer('Успешно удалено')
        await state.clear()
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")

    await sqlbase_for_places.close()


@router_for_places.callback_query(InlineMainMenu.filter(F.action == "edit_place"))
async def update_place(callback: CallbackQuery, state: FSMContext):
    await sqlbase_for_places.connect()
    check_login = await sqlbase_for_places.check_login()
    if check_login:
        kb = await keyboard_fabric.inline_admin_main_menu()
        await state.update_data(kb_place_edit=kb)
        n = ""
        mesage = await place_for(sqlbase_for_places)
        await state.update_data(local=mesage)
        kb = await keyboard_fabric.stop()
        for i in mesage:
            n += f'{mesage[i]}({i})\n'
        await callback.message.answer(f'Какое место вы хотите изменить. Ниже приведён список мест(Введите цифру):\n{n}',
                                      reply_markup=kb)
        await callback.answer()
        await state.set_state(UpdateAddress.name)
    else:
        await callback.answer('Вы не супер-администратор, у вас нет этой функции')


@router_for_places.message(UpdateAddress.name, F.text)
async def update_address_one(message: Message, state: FSMContext):
    user_number = ''
    data = await state.get_data()
    for nummer in data['local']:
        user_number += str(nummer)

    # Проверка на то существует ли место
    if message.text in user_number:
        value_data = data['local'][int(message.text)]
        await state.update_data(place=value_data)

        # Извлекаем данные из базы данных по адресу
        all_update = await sqlbase_for_places.execute_query(
            '''SELECT * FROM message WHERE place = $1 ORDER BY id ASC ''', (value_data,))
        await state.update_data(value_data=all_update)
        # Проверяем, что результат существует
        if all_update:
            img_blob = all_update[0][3]

            # Создаём поток из байтов
            image_stream = io.BytesIO(img_blob)
            image_stream.seek(0)

            photo = BufferedInputFile(file=image_stream.read(), filename="image.png")

            kb = [
                [types.KeyboardButton(text='Адрес'), types.KeyboardButton(text='Место')],
                [types.KeyboardButton(text='Сообщение')],
                [types.KeyboardButton(text='Фото')],
                [types.KeyboardButton(text="Стоп")]
            ]
            keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True,
                                                 input_field_placeholder='Выберите')
            await bot.send_photo(chat_id=message.from_user.id, caption=f'Это изначальные данные, выберите, что вы'
                                                                       f' хотите изменить:\n'
                                                                       f'Адрес места\n'
                                                                       f'Место\n'
                                                                       f'Сообщение к нему\n'
                                                                       f'Фото', photo=photo, reply_markup=keyboard)

            # Завершаем процесс
            await state.set_state(UpdateAddress.name_state)
    else:
        await message.answer("Этого места не существует")

        # Закрываем соединение с базой данных


@router_for_places.message(UpdateAddress.name_state)
async def update_address_too(message: Message, state: FSMContext):
    if message.text.lower() == 'адрес':
        await message.answer('Введите адрес')
        await state.set_state(UpdateAddress.address)

    elif message.text.lower() == 'место':
        await message.answer('Введите место')
        await state.set_state(UpdateAddress.name_place)

    elif message.text.lower() == 'сообщение':
        await message.answer('Введите сообщение')
        await state.set_state(UpdateAddress.messages)

    elif message.text.lower() == 'фото':
        await message.answer('Введите фото')
        await state.set_state(UpdateAddress.photo)


@router_for_places.message(UpdateAddress.address, F.text)
async def update_address_for_address(message: Message, state: FSMContext):
    data = await state.get_data()
    await sqlbase_for_places.execute_query(f'''UPDATE message SET address = $1 WHERE place = $2''', (message.text,
                                                                                                     data[
                                                                                                         'value_data'][
                                                                                                         0][4],))
    await message.answer(f'Успешно обновлён адрес в месте - {data["value_data"][0][4]}')
    await sqlbase_for_places.close()


@router_for_places.message(UpdateAddress.name_place, F.text)
async def address_name_place(message: Message, state: FSMContext):
    data = await state.get_data()
    await sqlbase_for_places.execute_query(f'''UPDATE message SET place = $1 WHERE place = $2''', (message.text,
                                                                                                   data[
                                                                                                       'value_data'][
                                                                                                       0][4],))

    await message.answer(f'Успешно обновлёно место в месте - {data["value_data"][0][4]}')
    await sqlbase_for_places.close()


@router_for_places.message(UpdateAddress.messages, F.text)
async def address_name_for_message(message: Message, state: FSMContext):
    if message.text.lower() == '':  # Проверяем, завершил ли пользователь процесс
        kb = await state.get_value("kb_place_edit")
        await message.answer("Принудительно завершён процесс изменения мест.", reply_markup=kb)
        await state.clear()
        await sqlbase_for_places.close()

    else:
        data = await state.get_data()
        await sqlbase_for_places.execute_query(f'''UPDATE message SET message = $1 WHERE place = $2''', (message.text,
                                                                                                         data[
                                                                                                             'value_data'][
                                                                                                             0][4],))

        await message.answer(f'Успешно обновлёно сообщение в месте - {data["value_data"][0][4]}')
        await sqlbase_for_places.close()


# Удаление по адресу
@router_for_places.callback_query(InlineMainMenu.filter(F.action == "remove_address"))
async def remove_place(callback: CallbackQuery, state: FSMContext):
    await sqlbase_for_places.connect()
    check_login = await sqlbase_for_places.check_login()
    if check_login:
        kb = await keyboard_fabric.inline_admin_main_menu()
        await state.update_data(kb_address_remove=kb)

        await callback.message.answer('*ВНИМАНИЕ! Вы удаляете по конкретному адресу - это означает, что все места '
                                      'этим адресом удалятся*\nКакое вы хотите удалить место из приложенного списка мест'
                                      '\nВведите место:', parse_mode='Markdown')
        address = await address_for(sqlbase_for_places)

        true_message = str(address)
        true_message = true_message.replace('{', '')
        true_message = true_message.replace('}', '')
        true_message = true_message.replace("'", '')

        await callback.message.answer(f'Вот все названия заведений: {true_message}')
        await callback.answer()

        await state.set_state(RemovePA.address)
    else:
        await callback.message.answer('Вы не супер-администратор, у вас нет этой функции')


@router_for_places.message(RemovePA.address, F.text)
async def remove_places(message: Message, state: FSMContext):
    await state.update_data(address=message.text)

    await sqlbase_for_places.execute_query('''DELETE FROM message WHERE address = $1''', (message.text,))
    await message.answer('Успешно удалено')
    await state.clear()

    await sqlbase_for_places.close()


# Удаление места
@router_for_places.callback_query(InlineMainMenu.filter(F.action == "remove_place"))
async def remove_place(callback: CallbackQuery, state: FSMContext):
    """Удаление мест"""
    await sqlbase_for_places.connect()
    check_login = await sqlbase_for_places.check_login()
    if check_login:
        kb = await keyboard_fabric.inline_admin_main_menu()
        await state.update_data(kb_remove_place=kb)
        mesage = await place_for(sqlbase_for_places)

        variantes = ''
        for nummer in mesage:
            variantes += f'{mesage[nummer]}\n'

        await callback.message.answer(
            f'*ВНИМАНИЕ! Вы удаляете по конкретному месту, а не по адресу*\nВведите место из списка, приложенного ниже:'
            f'\nВот все названия заведений:\n{variantes}', parse_mode='Markdown')
        await callback.answer()

        await state.set_state(RemovePA.place)
    else:
        await callback.answer('Вы не супер-администратор, у вас нет этой функции')


# Удаление по месту
@router_for_places.message(RemovePA.place, F.text)
async def remove_places(message: Message, state: FSMContext):
    await state.update_data(place=message.text)
    try:
        await sqlbase_for_places.execute_query('''DELETE FROM message WHERE place = $1 ''', (message.text,))
        await sqlbase_for_places.close()
        await state.clear()
        await message.answer('Успешно удалено')
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")
