import logging
import asyncio
import os
import psycopg2
from aiogram.filters import CommandStart
from aiogram.types import Message
from humanfriendly.terminal import message
from psycopg2 import Error
import time
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from psycopg2 import sql
import select
from pyexpat.errors import messages
from config import ip, PG_password, PG_user, DATABASE

logging.basicConfig(level=logging.INFO)
connection = psycopg2.connect(host=ip, user=PG_user, password=PG_password, database=DATABASE)
cursor = connection.cursor()
load_dotenv()
bot = Bot(token=os.getenv('API_KEY'))
dp = Dispatcher()



async def start_cmd():
    connection.autocommit = True
    # Для получения уведомлений
    try:
        with connection.cursor() as cur:
            # Подписываемся на канал уведомлений
            cur.execute(f"LISTEN {PG_user};")
            print("Ожидание уведомлений о новых данных...")
            cur.execute(f"SELECT adm_one, adm_too, adm_three FROM adm ORDER BY id DESC LIMIT 1;")
            rows = cur.fetchall()
            # print("Последние данные в таблице:")
            for row in rows:
                nice = row
                nice = list(nice)
                print(nice)

            while True:

                # Ожидание уведомлений
                if select.select([connection], [], [], 5) == ([], [], []):
                    pass
                # print("Нет новых уведомлений.")
                else:
                    connection.poll()
                    while connection.notifies:
                        notify = connection.notifies.pop(0)
                        # print(f"Уведомление получено: {notify.payload}")

                        # Получаем последние данные из таблицы
                        cur.execute(
                            f"SELECT Data_times, Place, Id_user, Rating, Review FROM servers ORDER BY id DESC LIMIT 1;")
                        rows = cur.fetchall()
                        # print("Последние данные в таблице:")
                        for row in rows:
                            row = list(row)
                            # print(type(row))
                            for i in range(3):
                                if nice[i] in 'None':
                                    pass
                                else:
                                    await bot.send_message(chat_id=nice[i], text=f'Дата: {row[0]}\nМесто: {row[1]} \nПользователь(id): {row[2]}\nРейтинг: {row[3]} \nОтзыв: {row[4]}')

                            #Подумать нунна ли cmd_start и сделать в row try и expect. Текущая цельЖ Обозначить админов автоматически
    except Error as e:
        # Откат изменений в случае ошибки
        connection.rollback()
        # Выводим сообщение об ошибке и ее код
        print(f"Transaction failed: {str(e)}")



async def start_c():
    await start_cmd()


async def main():
    await asyncio.create_task(start_cmd())

    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
