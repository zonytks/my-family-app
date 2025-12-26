import sqlite3

def init_db():
    conn = sqlite3.connect('family_hub.db')
    cursor = conn.cursor()
    
    # Таблица семей
    cursor.execute('''CREATE TABLE IF NOT EXISTS families 
                      (id INTEGER PRIMARY KEY, name TEXT, code TEXT UNIQUE)''')
    
    # Таблица пользователей
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, family_id INTEGER, name TEXT,
                       FOREIGN KEY(family_id) REFERENCES families(id))''')
    
    # Таблица покупок
    cursor.execute('''CREATE TABLE IF NOT EXISTS shopping 
                      (id INTEGER PRIMARY KEY, family_id INTEGER, item TEXT, is_done INTEGER DEFAULT 0)''')
    
    # Таблица дат
    cursor.execute('''CREATE TABLE IF NOT EXISTS events 
                      (id INTEGER PRIMARY KEY, family_id INTEGER, title TEXT, event_date TEXT)''')
    
    # Таблица паролей
    cursor.execute('''CREATE TABLE IF NOT EXISTS passwords 
                      (id INTEGER PRIMARY KEY, family_id INTEGER, service TEXT, password TEXT)''')
    
    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect('family_hub.db')

init_db() # Создаем базу при первом запуске