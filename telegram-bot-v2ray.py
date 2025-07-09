import requests
import json
import time

TOKEN = "8057495132:AAESf8cO_FbIfYC4DTp8uVBKTU_ECNiTznA"
ADMIN_ID = 2075973663
API = f'https://api.telegram.org/bot{TOKEN}'
CHANNEL_ID = '@channelusername'  # برای جوین اجباری
DATA_FILE = 'data.json'

# --- ذخیره و بارگذاری داده‌ها ---
def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {'config_urls': [], 'users': {}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

# --- ارسال پیام ---
def send_message(chat_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'text': text}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    requests.post(f'{API}/sendMessage', data=payload)

# --- دریافت آپدیت‌ها ---
def get_updates(offset=None):
    params = {'timeout': 30}
    if offset:
        params['offset'] = offset
    res = requests.get(f'{API}/getUpdates', params=params)
    return res.json()['result']

# --- بررسی عضویت در کانال ---
def is_member(user_id):
    url = f"{API}/getChatMember?chat_id={CHANNEL_ID}&user_id={user_id}"
    res = requests.get(url).json()
    status = res.get('result', {}).get('status', '')
    return status in ['member', 'administrator', 'creator']

# --- بررسی سلامت کانفیگ‌ها ---
def check_configs(url):
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200:
            return []
        configs = res.text.strip().splitlines()
        valid = []
        for c in configs:
            try:
                r = requests.get(c.strip(), timeout=5)
                if r.status_code == 200:
                    valid.append(c.strip())
            except:
                pass
        return valid
    except:
        return []

# --- ساخت دکمه‌ها از لینک‌ها ---
def make_inline_keyboard(urls):
    buttons = [[{'text': f'🔗 لینک {i+1}', 'callback_data': url}] for i, url in enumerate(urls)]
    return {'inline_keyboard': buttons}

# --- دکمه منو اصلی ---
def main_menu():
    return {
        'keyboard': [
            ['🧪 تست ساعتی'],
            ['📚 آموزش استفاده'],
            ['🌐 لیست سرورها']
        ],
        'resize_keyboard': True
    }

# --- پردازش پیام‌ها و دکمه‌ها ---
def process_message(update, data):
    message = update.get('message')
    callback = update.get('callback_query')

    if message:
        text = message.get('text')
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        username = message['from'].get('username', '')

        # ذخیره کاربر
        if str(user_id) not in data['users']:
            data['users'][str(user_id)] = {'joined': False}
            save_data(data)

        # جوین اجباری
        if not is_member(user_id):
            send_message(chat_id, f"⛔️ لطفاً ابتدا در کانال {CHANNEL_ID} عضو شوید.")
            return

        # دستورات عمومی
        if text == '/start':
            send_message(chat_id, "🎉 به ربات خوش آمدی. از منو استفاده کن:", main_menu())
        elif text == '📚 آموزش استفاده':
            send_message(chat_id, "📖 آموزش:\n1. ابتدا در کانال عضو شو\n2. روی لینک‌ها کلیک کن و تست بگیر\n3. فقط کانفیگ‌های سالم بهت داده میشه.")
        elif text == '🧪 تست ساعتی':
            send_message(chat_id, "⌛️ تست ساعتی فعلاً فعال نیست. به‌زودی اضافه می‌شود.")
        elif text == '🌐 لیست سرورها':
            if data['config_urls']:
                keyboard = make_inline_keyboard(data['config_urls'])
                send_message(chat_id, 'یکی از لینک‌های زیر رو برای بررسی انتخاب کن:', keyboard)
            else:
                send_message(chat_id, '⚠️ هنوز لینکی توسط ادمین ثبت نشده.')

        # لینک‌دهی توسط ادمین
        elif username == ADMIN_USERNAME and text.startswith('http'):
            data['config_urls'] = [x.strip() for x in text.strip().splitlines() if x.startswith('http')]
            save_data(data)
            send_message(chat_id, '✅ لینک‌ها ذخیره شدند.')

    elif callback:
        chat_id = callback['from']['id']
        user_id = callback['from']['id']
        url = callback['data']

        if not is_member(user_id):
            send_message(chat_id, f"⛔️ لطفاً ابتدا در کانال {CHANNEL_ID} عضو شوید.")
            return

        send_message(chat_id, '🔍 در حال بررسی کانفیگ‌ها...')
        valid = check_configs(url)
        if valid:
            msg = '✅ کانفیگ‌های سالم:\n' + '\n'.join(valid)
        else:
            msg = '❌ هیچ کانفیگ سالمی پیدا نشد.'
        send_message(chat_id, msg)

# --- حلقه اصلی ---
def main():
    data = load_data()
    last_update = None

    while True:
        updates = get_updates(last_update)
        for upd in updates:
            last_update = upd['update_id'] + 1
            process_message(upd, data)
        time.sleep(1)

if __name__ == '__main__':
    main()
