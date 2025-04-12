import os

from aiogram import Bot

from config import PG_user
from db.db import Sqlbase
bot = Bot(token=os.getenv('API_KEY'))
sqlbase = Sqlbase()
async def start_cmd(adm: str, count: int):
    await sqlbase.connect()
    id_back = await sqlbase.execute_query(f"SELECT id_back1, id_back2, id_back3, id_back4, id_back5, id_back6, id_back7, id_back8, id_back9, id_back10 FROM adm ORDER BY id DESC LIMIT 1;")
    await sqlbase.execute_query(f"LISTEN {PG_user};")

    last_processed_id = id_back[0][count]
    rows = await sqlbase.execute_query(
        f"SELECT id, Data_times, Place, Id_user, Rating, Review FROM servers WHERE id > {last_processed_id} ORDER BY id ASC;")
    result = await sqlbase.execute_query("SELECT MAX(id) FROM servers;")

    if result and result[0]:
        last_processed_id = result[0][0]
        await sqlbase.execute_query(f"UPDATE adm SET id_back{count+1} = $1 WHERE id=1", (last_processed_id ,))
    await sqlbase.close()

    for row in rows:
        message = (f"Дата: {row[1]}\n"
                   f"Место: {row[2]}\n"
                   f"Пользователь(id): {row[3]}\n"
                   f"Рейтинг: {row[4]}\n"
                   f"Отзыв: {row[5]}")
        await bot.send_message(chat_id=adm, text=message)

