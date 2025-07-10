from db.db import Sqlbase


async def place_for(sqlbase: Sqlbase):
    dictes = {}
    place = await sqlbase.execute_query('SELECT place FROM message')
    for number, names in enumerate(place):
        dictes[number + 1] = names[0]
    return dictes


# Получение адресов
async def address_for(sqlbase: Sqlbase):
    place = await sqlbase.execute_query('SELECT address FROM message')
    first = {row[0] for row in place}
    return first
