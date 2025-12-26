import asyncio
import os
import logging
import random
import string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo
from aiohttp import web
import database as db

# --- НАСТРОЙКИ ---
API_TOKEN = '8295389778:AAFH6K0850o_zIfSzraiReSI3mrDC1ELj70'
# Эта переменная автоматически подхватит адрес от Render
WEB_APP_URL = os.getenv("RENDER_EXTERNAL_URL", "https://your-app.onrender.com")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- ЛОГИКА ВЕБ-СЕРВЕРА (API) ---

async def serve_index(request):
    return web.FileResponse('index.html')

async def get_data(request):
    user_id = int(request.rel_url.query.get('user_id', 0))
    conn = db.get_db()
    cur = conn.cursor()
    cur.execute("SELECT family_id FROM users WHERE user_id = ?", (user_id,))
    fid = cur.fetchone()
    if not fid or not fid[0]: return web.json_response({"shopping": [], "events": [], "passwords": []})
    fid = fid[0]
    
    cur.execute("SELECT id, item, is_done FROM shopping WHERE family_id = ?", (fid,))
    shopping = [{"id": r[0], "text": r[1], "done": r[2]} for r in cur.fetchall()]
    
    cur.execute("SELECT id, title, event_date FROM events WHERE family_id = ?", (fid,))
    events = [{"id": r[0], "title": r[1], "date": r[2]} for r in cur.fetchall()]
    
    cur.execute("SELECT id, service, password FROM passwords WHERE family_id = ?", (fid,))
    passwords = [{"id": r[0], "service": r[1], "pass": r[2]} for r in cur.fetchall()]
    
    conn.close()
    return web.json_response({"shopping": shopping, "events": events, "passwords": passwords})

async def add_data(request):
    data = await request.json()
    uid, text, table = data.get('user_id'), data.get('text'), data.get('table')
    conn = db.get_db()
    cur = conn.cursor()
    cur.execute("SELECT family_id FROM users WHERE user_id = ?", (uid,))
    fid = cur.fetchone()[0]
    
    if table == 'shopping':
        cur.execute("INSERT INTO shopping (family_id, item) VALUES (?, ?)", (fid, text))
    elif table == 'events' and '|' in text:
        t, d = text.split('|')
        cur.execute("INSERT INTO events (family_id, title, event_date) VALUES (?, ?, ?)", (fid, t.strip(), d.strip()))
    elif table == 'passwords' and '|' in text:
        s, p = text.split('|')
        cur.execute("INSERT INTO passwords (family_id, service, password) VALUES (?, ?, ?)", (fid, s.strip(), p.strip()))
    
    conn.commit()
    conn.close()
    return web.json_response({"status": "ok"})

async def toggle_item(request):
    data = await request.json()
    conn = db.get_db()
    cur = conn.cursor()
    cur.execute("UPDATE shopping SET is_done = 1 - is_done WHERE id = ?", (data['id'],))
    conn.commit()
    conn.close()
    return web.json_response({"status": "ok"})

# --- ЛОГИКА БОТА ---

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    conn = db.get_db()
    cur = conn.cursor()
    cur.execute("SELECT family_id FROM users WHERE user_id = ?", (message.from_user.id,))
    user = cur.fetchone()
    
    if user and user[0]:
        url = f"{WEB_APP_URL}?user_id={message.from_user.id}"
        kb = [[types.KeyboardButton(text="🏠 Открыть Family Hub", web_app=WebAppInfo(url=url))]]
        await message.answer("Приложение готово!", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    else:
        await message.answer("Вы не в семье. \n1. /create - создать семью\n2. /join КОД - войти")
    conn.close()

@dp.message(Command("create"))
async def create_family(message: types.Message):
    code = generate_code()
    conn = db.get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO families (name, code) VALUES (?, ?)", (f"Семья {message.from_user.first_name}", code))
    fid = cur.lastrowid
    cur.execute("INSERT OR REPLACE INTO users (user_id, family_id, name) VALUES (?, ?, ?)", (message.from_user.id, fid, message.from_user.first_name))
    conn.commit()
    conn.close()
    await message.answer(f"Семья создана! Код: {code}")

@dp.message(Command("join"))
async def join_family(message: types.Message):
    code = message.text.split()[-1].upper()
    conn = db.get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM families WHERE code = ?", (code,))
    family = cur.fetchone()
    if family:
        cur.execute("INSERT OR REPLACE INTO users (user_id, family_id, name) VALUES (?, ?, ?)", (message.from_user.id, family[0], message.from_user.first_name))
        conn.commit()
        await message.answer("Успешно! Напишите /start")
    else:
        await message.answer("Код не найден.")
    conn.close()

@dp.message(Command("leave"))
async def leave_family(message: types.Message):
    conn = db.get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET family_id = NULL WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer("Вы вышли из семьи.")

# --- ЗАПУСК ---

async def main():
    app = web.Application()
    app.router.add_get('/', serve_index)
    app.router.add_get('/get_data', get_data)
    app.router.add_post('/add_data', add_data)
    app.router.add_post('/toggle_item', toggle_item)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    await site.start()
    logging.info(f"Сервер запущен на порту {port}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())