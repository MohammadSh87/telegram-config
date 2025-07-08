


import requests
import zipfile
import io
import os
import json
import time


TOKEN = '8057495132:AAESf8cO_FbIfYC4DTp8uVBKTU_ECNiTznA'
ADMIN_USERNAME = 'Mohammad87killer'
BASE_URL = f'https://api.telegram.org/bot{TOKEN}'
GITHUB_ZIP_URL = "https://github.com/Epodonios/v2ray-configs/archive/refs/heads/main.zip"
CONFIG_FOLDER = "v2ray-configs/v2ray-configs-main"

# دریافت آپدیت‌ها
def get_updates(offset=None):
    url = BASE_URL + '/getUpdates'
    params = {'timeout': 100, 'offset': offset}
    res = requests.get(url, params=params)
    return res.json()

# ارسال پیام
def send_message(chat_id, text, reply_markup=None):
    url = BASE_URL + '/sendMessage'
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    requests.post(url, data=data)

# دانلود و استخراج کانفیگ‌ها از گیت‌هاب
def download_configs():
    if os.path.exists(CONFIG_FOLDER):
        return
    r = requests.get(GITHUB_ZIP_URL)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall("v2ray-configs")

# استخراج لیست سرورها از فایل‌ها
def list_configs():
    files = [f for f in os.listdir(CONFIG_FOLDER) if f.endswith('.json')]
    configs = []
    for f in files:
        try:
            with open(os.path.join(CONFIG_FOLDER, f), "r", encoding="utf-8") as file:
                config = json.load(file)
                server_name = config.get('ps', f)
                configs.append((server_name, f))
        except:
            continue
    return configs

# دریافت متن کانفیگ به‌صورت متن
def get_config_text(filename):
    try:
        with open(os.path.join(CONFIG_FOLDER, filename), "r", encoding="utf-8") as file:
            return file.read()
    except:
        return "خطا در خواندن فایل کانفیگ."

# حلقه اصلی ربات
def main():
    print("ربات در حال اجراست...")
    download_configs()
    last_update_id = None

    while True:
        updates = get_updates(last_update_id)
        if 'result' in updates:
            for update in updates['result']:
                last_update_id = update['update_id'] + 1

                if 'message' in update:
                    chat_id = update['message']['chat']['id']
                    text = update['message'].get('text', '')

                    if text == '/start':
                        send_message(chat_id, "سلام! لطفا یکی از سرورهای زیر را انتخاب کنید:")

                        buttons = []
                        configs = list_configs()
                        for name, file in configs[:10]:  # فقط ۱۰ تا اول
                            buttons.append([{'text': name, 'callback_data': f'get_{file}'}])

                        send_message(chat_id, "لیست سرورها:", {
                            'inline_keyboard': buttons
                        })

                elif 'callback_query' in update:
                    callback = update['callback_query']
                    data = callback['data']
                    chat_id = callback['message']['chat']['id']
                    message_id = callback['message']['message_id']

                    if data.startswith("get_"):
                        filename = data[4:]
                        config_text = get_config_text(filename)
                        send_message(chat_id, f"<code>{config_text}</code>")

        time.sleep(1)

if __name__ == '__main__':
    main()


