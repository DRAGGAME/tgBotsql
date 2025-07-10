import asyncpg

# Загружаем переменные из .env
from config import HOST, PASSWORD, DATABASE, USER

pg_host = HOST
pg_user = USER
pg_password = PASSWORD
pg_database = DATABASE


class Sqlbase:
    def __init__(self):
        self.pool = None

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(
                host=pg_host,
                user=pg_user,
                password=pg_password,
                database=pg_database,
                min_size=1,
                max_size=10000
            )
        except Exception as e:
            print(f"Ошибка подключения к базе данных: {e}")
            raise

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def execute_query(self, query, params=None) -> tuple:
        if not self.pool:
            raise ValueError("Пул соединений не создан. Убедитесь, что вызвали connect().")
        try:
            async with self.pool.acquire() as connection:
                async with connection.transaction():
                    if params:
                        return await connection.fetch(query, *params)
                    return await connection.fetch(query)

        except asyncpg.PostgresError as e:

            print(f"Ошибка выполнения запроса: {e}")
            raise

    async def insert_new_query(self, chat_id: int, username: str):
        await self.execute_query("""INSERT INTO admin_list_table (chat_id, Username) VALUES ($1, $2)""",
                                 (str(chat_id), username))

    async def update_state_admin(self, chat_id: int):
        active = True
        if chat_id == 0:
            active = False
        await self.execute_query("""UPDATE settings_for_admin SET superuser_active = $1, superuser_chat_id=$2;""",
                                 (active, str(chat_id),))

    async def update_inactive(self, inactive: bool, chat_id: int):
        if chat_id != 0:
            await self.execute_query("""UPDATE admin_list_table SET activate=$1 WHERE chat_id=$2""",
                                     (inactive, str(chat_id),))
        else:
            await self.execute_query("""UPDATE admin_list_table SET activate=$1""",
                                     (inactive,))

    async def delete_admins(self, chat_id: int):
        await self.execute_query("""DELETE FROM admin_list_table WHERE chat_id=$1""", (str(chat_id),))

    async def check_login(self) -> bool:
        check_active = await self.execute_query("""SELECT superuser_active FROM settings_for_admin""")
        return check_active[0][0]

    async def insert_message(self, address, message, photo, place):
        query = '''
            INSERT INTO message (address, message, photo, place)
            VALUES ($1, $2, $3, $4);
        '''
        await self.execute_query(query, (address, message, photo, place))

    async def delete(self):
        query = "DROP TABLE IF EXISTS servers;"
        await self.execute_query(query)


if __name__ == '__main__':
    sqlbase = Sqlbase()
