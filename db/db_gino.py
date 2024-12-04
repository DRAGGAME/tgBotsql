import psycopg2
from psycopg2 import sql
from psycopg2 import Error

from config import ip, PG_user, DATABASE, PG_password
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Sqlbase:
    def __init__(self):
        self.connection = psycopg2.connect(host=ip, user=PG_user, password=PG_password, database=DATABASE)
        self.connection.autocommit=False
        self.cursor = self.connection.cursor()


    def spaltenerstellen(self):
        # Создание столбцов
        try:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS adm(
                                Id SERIAL PRIMARY KEY,
                                Adm_one text,
                                Adm_too text,
                                Adm_three text
                                );''')
            self.connection.commit()
        except Error as e:
            # Откат изменений в случае ошибки
            self.connection.rollback()
            # Выводим сообщение об ошибке и ее код
            print(f"Transaction failed: {e.pgcode} - {e.pgerror}")

        finally:
            if self.connection:
                self.cursor.close()
                self.connection.close()
                print('Всё окей')


    def spaltenausgabe(self):
        try:
            query = sql.SQL("SELECT {fields} FROM {table} WHERE {pkey} = %s;").format(
                    fields=sql.SQL(', ').join([
                        sql.Identifier('id'),
                        sql.Identifier('data_times'),
                        sql.Identifier('place'),
                        sql.Identifier('id_user'),
                        sql.Identifier('rating'),
                        sql.Identifier('review')
                    ]),
                    table=sql.Identifier('servers'),
                    pkey=sql.Identifier('id')
                )
            self.cursor.execute(query, (1,))
            self.connection.commit()
            print(self.cursor.fetchone())
        except Error as e:
            # Откат изменений в случае ошибки
            self.connection.rollback()
            # Выводим сообщение об ошибке и ее код
            print(f"Transaction failed: {e.pgcode} - {e.pgerror}")

        finally:
            if self.connection:
                self.cursor.close()
                self.connection.close()
                print('Всё окей')
    '''time, place, user, rating, review, - При вставке в таблицу servers. Если для получения, таблица adm'''
    def ins(self, adm1, adm2, adm3):
        try:
            self.cursor.execute("INSERT INTO servers (adm_one, adm_too, adm_three) VALUES (%s, %s, %s);", (adm1, adm2, adm3))

            self.cursor.execute(f"NOTIFY {PG_user}, 'Данные обновлены';")
            self.connection.commit()
        except Error as e:
            # Откат изменений в случае ошибки
            self.connection.rollback()
            # Выводим сообщение об ошибке и ее код
            print(f"Transaction failed: {str(e)}")

        # finally:
        #     if self.connection:
        #         self.cursor.close()
        #         self.connection.close()
        #         print('Всё окей')

    def selectes(self):
        try:
            with self.connection.cursor() as cur:
                cur.execute(f"LISTEN {PG_user};")
                print("Ожидание уведомлений о новых данных...")
                cur.execute(f"SELECT adm_one, adm_too, adm_three FROM adm ORDER BY id DESC LIMIT 1;")
                rows = cur.fetchall()
                # print("Последние данные в таблице:")
                for row in rows:
                    nice = row
                    nice = list(nice)
                return nice


        except Error as e:
            # Откат изменений в случае ошибки
            self.connection.rollback()
            # Выводим сообщение об ошибке и ее код
            print(f"Transaction failed: {str(e)}")

    def delete(self):
        try:
            self.cursor.execute("DROP TABLE adm;")
            self.connection.commit()

        except Error as e:
            # Откат изменений в случае ошибки
            self.connection.rollback()
            # Выводим сообщение об ошибке и ее код
            print(f"Transaction failed: {str(e)}")

        finally:
            if self.connection:
                self.cursor.close()
                self.connection.close()
                print('Всё круто')
if __name__ == '__main__':

    test_sql_class = Sqlbase()
    test_sql_class.selectes()
    # test_sql_class.delete()
    # test_sql_class.spaltenerstellen()
    # test_sql_class.ins('2005683766', 'None', 'None')
