from db.db import Sqlbase


class CreateTable(Sqlbase):

    async def create_table_reviews(self) -> None:

        """
        Создание таблицы, куда отправляются отзывы
        """

        query = ''' 
            CREATE TABLE IF NOT EXISTS reviews (
                Id SERIAL PRIMARY KEY,
                id_user TEXT NOT NULL,
                data_times TEXT NOT NULL,
                address TEXT NOT NULL,
                place TEXT NOT NULL,
                rating SMALLINT NOT NULL,
                review TEXT NOT NULL
            );
        '''
        await self.execute_query(query)

    async def create_table_settings_for_review(self) -> None:

        """
        Создание таблицы для бота для клиентов
        """

        query = '''CREATE TABLE IF NOT EXISTS settings_for_review_bot (
            Id SERIAL PRIMARY KEY,
            review_or_rating_message TEXT NOT NULL, 
            review_message TEXT NOT NULL
        );'''
        await self.execute_query(query)

        review_or_rating = 'Оценка принята. Если вы желаете написать отзыв, то напишите "Да", если нет, то "Нет".'
        review_message = 'Напишите, пожалуйста, отзыв'

        await self.execute_query(
            '''INSERT INTO settings_for_review_bot (review_or_rating_message, review_message) 
               VALUES ($1, $2)''',
            (review_or_rating, review_message)
        )


    async def create_table_adm_settings(self) -> None:
        """
        Создание таблицы для настроек связанных с админами
        """
        query = '''CREATE TABLE IF NOT EXISTS settings_for_admin (
            Id SERIAL PRIMARY KEY,
            bot_name TEXT 
        );'''

        await self.execute_query(query)

    async def create_table_admin_users(self) -> None:

        """
        Создание таблицы с пользователями-админами
        """

        query = '''
        CREATE TABLE IF NOT EXISTS admin_list_table (
        Id SERIAL PRIMARY KEY,
        User_id TEXT NOT NULL,
        Username TEXT NOT NULL,
        last_id_message TEXT NOT NULL
        );'''

        await self.execute_query(query)



