from config import bot
from db.db import Sqlbase


async def start_cmd(chat_id: str, pool_sqlbase: Sqlbase):
    last_message_id = await pool_sqlbase.execute_query(f"SELECT last_id_message "
                                                       f"FROM admin_list_table WHERE chat_id = $1 ORDER BY id ASC;",
                                                       (chat_id,))

    reviews = await pool_sqlbase.execute_query(
        f"SELECT * FROM reviews WHERE id > {last_message_id[0][0]} ORDER BY id ASC;")

    if not reviews:
        return

    max_id = await pool_sqlbase.execute_query("SELECT MAX(id) FROM reviews;")
    await pool_sqlbase.execute_query(f"UPDATE admin_list_table SET last_id_message = $1 WHERE chat_id = $2",
                                     (str(max_id[0][0]), str(chat_id),))

    for review in reviews:
        true_review = "Нет" if review[6] is None else review[6]
        message = (f"Дата: {review[2]}\n"
                   f"Место: {review[4]}\n"
                   f"Пользователь: {review[1]}\n"
                   f"Рейтинг: {review[5]}\n"
                   f"Отзыв: {true_review}")

        await bot.send_message(chat_id=chat_id, text=message)
