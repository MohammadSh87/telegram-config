

import requests
import json
import time
import os

# ========== تنظیمات ==========

TOKEN = '8057495132:AAESf8cO_FbIfYC4DTp8uVBKTU_ECNiTznA'
ADMIN_USERNAME = 'Mohammad87killer'
CHANNEL_USERNAME = '@channel'  # فقط جهت توسعه آتی
BASE_URL = f'https://api.telegram.org/bot{TOKEN}'
DB_FILE = 'users.json'

# ========== تابع‌های کمکی ==========
def save_users(users):
    with open(DB_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def load_users():
    if not os.path.exists(DB_FILE):
        save_users({})
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def send_message(chat_id, text, buttons=None):
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if buttons:
        data['reply_markup'] = json.dumps({'inline_keyboard': buttons})
    requests.post(f"{BASE_URL}/sendMessage", data=data)

def get_me():
    res = requests.get(f"{BASE_URL}/getMe").json()
    return res.get('result', {}).get('username', 'Bot')

# ========== ساختار دکمه‌ها ==========
def main_buttons():
    return [
        [{'text': '🛍 فروشگاه', 'callback_data': 'store'}],
        [{'text': '📊 وضعیت حساب', 'callback_data': 'status'}],
        [{'text': '📢 درباره ما', 'callback_data': 'about'}]
    ]

def admin_buttons():
    return [
        [{'text': '📬 ارسال پیام همگانی', 'callback_data': 'broadcast'}],
        [{'text': '📊 تعداد کاربران', 'callback_data': 'users'}]
    ]

# ========== پیام‌های پیش‌فرض ==========
def welcome_msg(user):
    return f"""سلام <b>{user['first_name']}</b> 👋

به ربات خوش آمدی!
از منو برای ادامه استفاده کن."""

def about_msg():
    return "رباتی ساده برای فروش کانفیگ V2Ray"

def store_msg():
    return "💥 در حال حاضر محصولی برای نمایش نیست."

# ========== پردازش آپدیت ==========
def handle_update(update, users):
    if 'message' in update:
        msg = update['message']
        user_id = str(msg['from']['id'])
        username = msg['from'].get('username', '')
        first_name = msg['from'].get('first_name', '')
        text = msg.get('text', '')

        if user_id not in users:
            users[user_id] = {
                'id': user_id,
                'first_name': first_name,
                'username': username,
                'joined': time.time(),
                'ref': None
            }
            save_users(users)

        if text == '/start':
            send_message(user_id, welcome_msg(msg['from']), main_buttons())

    elif 'callback_query' in update:
        query = update['callback_query']
        data = query['data']
        user_id = str(query['from']['id'])

        if data == 'about':
            send_message(user_id, about_msg())
        elif data == 'store':
            send_message(user_id, store_msg())
        elif data == 'status':
            user = users.get(user_id, {})
            joined = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(user.get('joined', 0)))
            send_message(user_id, f"🆔 <b>{user_id}</b>\n👤 <b>{user.get('first_name')}</b>\n⏰ ورود: {joined}")
        elif data == 'users' and query['from'].get('username') == ADMIN_USERNAME:
            send_message(user_id, f"👥 تعداد کاربران: {len(users)}")
        elif data == 'broadcast' and query['from'].get('username') == ADMIN_USERNAME:
            send_message(user_id, "📨 پیام مورد نظر را ارسال کنید (در حال توسعه).")

# ========== حلقه اصلی ==========
def main():
    print("ربات فعال شد.")
    users = load_users()
    last_update_id = None

    while True:
        try:
            params = {'timeout': 100, 'offset': last_update_id}
            res = requests.get(f"{BASE_URL}/getUpdates", params=params).json()

            for update in res.get('result', []):
                last_update_id = update['update_id'] + 1
                handle_update(update, users)

            time.sleep(1)
        except Exception as e:
            print("❌ خطا:", e)
            time.sleep(3)

if __name__ == '__main__':
    main()

