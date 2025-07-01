from config import bot
from db.db import Sqlbase

async def back_id(sqlbase_back: Sqlbase, chat_id: int):
    max_id = await sqlbase_back.execute_query("SELECT MAX(id) FROM servers;")
    await sqlbase_back.execute_query('''UPDATE admin_list_table SET last_id_message = $1 WHERE chat_id = $2''', (int(max_id[0][0]), str(chat_id)))

