import os

from aiogram import Bot

from config import api_key
from db.db import Sqlbase


bot = Bot(token=api_key, parce_mode='MARKDOWN')

sqlbase = Sqlbase()

async def back_id(sqlbase_back):
    max_id = await sqlbase_back.execute_query("SELECT MAX(id) FROM servers;")
    await sqlbase_back.execute_query('''UPDATE adm SET id_back1 = $1, id_back2 = $1, id_back3 = $1, id_back4 = $1,
    id_back5 = $1, id_back6 = $1, 
    id_back7 = $1, id_back8 = $1,
     id_back9 = $1, id_back10 = $1''', (int(max_id[0][0]), ))
    await bot.session.close()

