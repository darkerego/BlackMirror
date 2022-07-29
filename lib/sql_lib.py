import os
import sys
import sqlite3
print(os.getcwd())
from threading import Lock


class SQLLiteConnection:
    def __init__(self, dbname=f"ftxdb.sqlite"):
        self.dbName = dbname
        print(f'Connecting to  {self.dbName}')
        self.conn = sqlite3.connect(self.dbName)
        self.lock = Lock()
        conn = self.conn

        # check DB
        self.lock.acquire()
        curs = conn.cursor()
        curs.execute("""create table if not exists orders ('values' TEXT)""")
        conn.commit()
        curs.execute("""create table if not exists profiles ('values' TEXT)""")
        conn.commit()
        curs.execute("""create table if not exists admin ('values' TEXT)""")
        conn.commit()
        curs.execute("""create table if not exists client_orders ('values' TEXT)""")
        conn.commit()
        curs.execute("""create table if not exists pnl ('pnl' TEXT)""")
        conn.commit()
        curs.execute("""create table if not exists brain ('brain' TEXT)""")
        conn.commit()
        curs.execute("""create table if not exists futures ('futures' TEXT)""")
        conn.commit()
        curs.execute("""create table if not exists listings ('listings' TEXT)""")
        curs.execute("""create table if not exists signals ('values' TEXT)""")
        conn.commit()
        curs.execute("""create table if not exists stats ('listings' TEXT)""")
        conn.commit()
        conn.close()
        self.lock.release()

    def add_table(self, name):
        self.lock.acquire()
        curs = self.conn.cursor()
        curs.execute(f"""create table if not exists {name} ('values' TEXT)""")
        self.conn.commit()
        self.lock.release()
        self.lock.release()

    def search(self, value, table='orders'):
        self.lock.acquire()
        conn = sqlite3.connect(self.dbName)
        curs = conn.cursor()
        value = str(value)
        curs.execute(f"SELECT * FROM {table} WHERE (?)", (value,))
        conn.commit()
        conn.close()
        self.lock.release()

    def append(self, value, table='orders'):

        self.lock.acquire()
        conn = sqlite3.connect(self.dbName)
        curs = conn.cursor()
        value = str(value)
        curs.execute(f"INSERT INTO {table} VALUES(?)", (value, ))
        conn.commit()
        conn.close()
        self.lock.release()

    def get_list(self, table='orders'):
        self.lock.acquire()
        conn = sqlite3.connect(self.dbName)
        curs = conn.cursor()
        curs.execute(f"SELECT * from {table}" )
        rows = curs.fetchall()
        res = []
        for row in rows:
            res.append(row[0])
        conn.commit()
        conn.close()
        self.lock.release()
        return res

    def remove(self, item, table='orders'):
        self.lock.acquire()
        conn = sqlite3.connect(self.dbName)
        curs = conn.cursor()
        item = str(item)

        curs.execute(f"delete from  {table} where `values`=?", (item, ))
        conn.commit()
        conn.close()
        self.lock.release()

    def clear(self, table='orders'):
        self.lock.acquire()
        conn = sqlite3.connect(self.dbName)
        curs = conn.cursor()
        curs.execute(f"delete from {table}")
        conn.commit()
        conn.close()
        self.lock.release()

    def disconnect(self):
        self.disconnect()