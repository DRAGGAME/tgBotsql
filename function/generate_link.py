import base64

async def generate_deep_link(sql_object, place_name: str):
    encoded_place = base64.urlsafe_b64encode(place_name.encode('utf-8')).decode('utf-8')
    # Кодируем место
    bot_username = await sql_object.execute_query('''SELECT bot_name FROM settings_for_admin''')
    bot_username = bot_username[0][0]
    if bot_username:
        if bot_username[0] == '@':
            bot_username = bot_username[1:]

        bot_username = bot_username.rstrip()

        return f"https://t.me/{bot_username}?start={encoded_place}"
    else:
        return None