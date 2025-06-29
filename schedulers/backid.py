
from config import bot
from db.db import Sqlbase

sqlbase = Sqlbase()

async def back_id(sqlbase_back):
    max_id = await sqlbase_back.execute_query("SELECT MAX(id) FROM servers;")
    await sqlbase_back.execute_query('''UPDATE adm SET last_id_message = $1''', (int(max_id[0][0]), ))

