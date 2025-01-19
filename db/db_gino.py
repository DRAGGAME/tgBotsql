import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()
user = os.getenv('PG_user')
password = os.getenv('PG_password')
ip = os.getenv('ip')
database = os.getenv('database')

'''Класс для работы с БД'''


class Sqlbase:
    def __init__(self):
        self.connection = None

    async def connect(self):
        try:
            self.connection = await asyncpg.connect(
                host=ip,
                user=user,
                password=password,
                database=database,
            )
            print("Соединение с базой данных установлено.")
        except Exception as e:
            print(f"Ошибка подключения к базе данных: {e}")
            raise

    async def close(self):
        if self.connection:

            await self.connection.close()
            print("Соединение с базой данных закрыто.")

    async def execute_query(self, query, params=None):
        if not self.connection:
            raise ValueError("Соединение не установлено. Убедитесь, что вызвали connect().")

        try:
            async with self.connection.transaction():
                if params:
                    result = await self.connection.fetch(query, *params)
                else:
                    result = await self.connection.fetch(query)
                return result
        except asyncpg.PostgresError as e:
            print(f"Ошибка выполнения запроса: {e}")
            raise

    async def spaltenerstellen(self):
        query = '''
            CREATE TABLE IF NOT EXISTS message (
                Id SERIAL PRIMARY KEY,
                address TEXT,
                message TEXT,
                photo TEXT,
                place TEXT
            );
        '''
        await self.execute_query(query)

    async def ins(self, address, message, photo, place):
        query = '''
            INSERT INTO message (address, message, photo, place)
            VALUES ($1, $2, $3, $4);
        '''
        await self.execute_query(query, (address, message, photo, place))

    async def delete(self):
        query = "DROP TABLE IF EXISTS message;"
        await self.execute_query(query)


if __name__ == '__main__':
    sqlbase = Sqlbase()

    async def main():
        # Проверяем переменные окружения
        print(f"user: {user}, password: {password}, ip: {ip}, database: {database}")

        # Подключаемся к базе данных
        await sqlbase.connect()

        try:
            # Создаём таблицу
            await sqlbase.spaltenerstellen()
            print("Таблица успешно создана.")

        finally:
            # Закрываем соединение
            await sqlbase.close()

    asyncio.run(main())
