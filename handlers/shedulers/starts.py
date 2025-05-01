import os

from aiogram import Bot

from config import PG_user, api_key

bot = Bot(token=api_key, parce_mode='MARKDOWN')

async def start_cmd(adm: str, count: int, pool_sqlbase):

    id_back = await pool_sqlbase.execute_query(f"SELECT id_back1, id_back2, id_back3, id_back4, id_back5, id_back6, id_back7, id_back8, id_back9, id_back10 FROM adm ORDER BY id DESC LIMIT 1;")
    await pool_sqlbase.execute_query(f"LISTEN {PG_user};")

    last_processed_id = id_back[0][count]
    rows = await pool_sqlbase.execute_query(
        f"SELECT id, Data_times, Place, Id_user, Rating, review FROM servers WHERE id > {last_processed_id} ORDER BY id ASC;")
    result = await pool_sqlbase.execute_query("SELECT MAX(id) FROM servers;")

    if result and result[0]:                  
        last_processed_id = result[0][0]
        await pool_sqlbase.execute_query(f"UPDATE adm SET id_back{count + 1} = $1 WHERE id=1", (last_processed_id ,))

    for row in rows:
        message = (f"Дата: {row[1]}\n"
                   f"Место: {row[2]}\n"
                   f"Пользователь: {row[3]}\n"
                   f"Рейтинг: {row[4]}\n"
                   f"Отзыв: {row[5]}")
        await bot.send_message(chat_id=adm, text=message)
    await bot.session.close()

