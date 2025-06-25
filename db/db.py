import asyncio
import asyncpg
import os
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


    async def execute_query(self, query, params=None):
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


    async def ins(self, address, message, photo, place):
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

