import requests
import time
import json
import os
import threading
import subprocess

TOKEN = "8057495132:AAESf8cO_FbIfYC4DTp8uVBKTU_ECNiTznA"
ADMIN_ID = 2075973663
API_URL = f'https://api.telegram.org/bot{TOKEN}'

DATA_FILE = "data.json"
USERS_FILE = "users.json"
CONFIGS_DIR = "files/configs"
VIDEOS_DIR = "files/videos"

# لود داده‌ها
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"admins": {}, "join_channel": "", "ping_interval": 300}, f)
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)
if not os.path.exists(CONFIGS_DIR):
    os.makedirs(CONFIGS_DIR)
if not os.path.exists(VIDEOS_DIR):
    os.makedirs(VIDEOS_DIR)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def telegram_request(method, params=None, files=None):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    try:
        if files:
            r = requests.post(url, data=params, files=files, timeout=15)
        else:
            r = requests.post(url, data=params, timeout=15)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get_updates(offset=None, timeout=20):
    params = {"timeout": timeout, "offset": offset}
    result = telegram_request("getUpdates", params)
    if result["ok"]:
        return result["result"]
    return []

def send_message(chat_id, text, reply_markup=None):
    params = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        params["reply_markup"] = json.dumps(reply_markup)
    telegram_request("sendMessage", params)

def send_document(chat_id, file_path, caption=None):
    with open(file_path, "rb") as f:
        params = {"chat_id": chat_id}
        if caption:
            params["caption"] = caption
        telegram_request("sendDocument", params, files={"document": f})

def check_user_joined_channel(user_id, channel):
    """
    channel می‌تواند آیدی عددی یا نام کاربری کانال با @ باشد
    """
    try:
        # اگر channel عدد است (آیدی)، به صورت عدد بفرستید
        try:
            chat_id = int(channel)
        except ValueError:
            chat_id = channel  # فرض می‌گیریم رشته‌ی @username است

        res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getChatMember", 
                           params={"chat_id": chat_id, "user_id": user_id}).json()
        if res["ok"]:
            status = res["result"]["status"]
            return status in ["member", "creator", "administrator"]
    except:
        pass
    return False

def ping_host(host):
    try:
        completed = subprocess.run(["ping", "-c", "1", "-W", "1", host], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return completed.returncode == 0
    except:
        return False

def extract_configs_from_link(link):
    try:
        r = requests.get(link, timeout=10)
        if r.status_code == 200:
            filename = os.path.join(CONFIGS_DIR, f"{int(time.time())}.conf")
            with open(filename, "wb") as f:
                f.write(r.content)
            hosts = []
            for line in r.text.splitlines():
                line=line.strip()
                if line and not line.startswith("#"):
                    hosts.append(line)
            return filename, hosts
    except:
        pass
    return None, []

def test_configs(hosts):
    healthy_hosts = []
    for h in hosts:
        if ping_host(h):
            healthy_hosts.append(h)
    return healthy_hosts

def admin_panel(chat_id):
    buttons = [
        [{"text": "تنظیم لینک کانفیگ", "callback_data": "set_link"}],
        [{"text": "تنظیم کانال جوین اجباری", "callback_data": "set_channel"}],
        [{"text": "آپلود ویدیو آموزشی", "callback_data": "upload_video"}],
        [{"text": "تنظیم زمان تست مجدد کانفیگ", "callback_data": "set_ping_interval"}],
        [{"text": "نمایش ویدیوهای آموزشی", "callback_data": "list_videos"}]
    ]
    send_message(chat_id, "پنل ادمین:", {"inline_keyboard": buttons})

def user_menu(chat_id):
    buttons = [
        [{"text": "دریافت کانفیگ‌های سالم", "callback_data": "get_healthy_configs"}],
        [{"text": "مشاهده ویدیوهای آموزشی", "callback_data": "list_videos"}]
    ]
    send_message(chat_id, "منوی کاربر:", {"inline_keyboard": buttons})

def handle_message(msg):
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    text = msg.get("text", "")

    data = load_data()
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {"joined": False}
        save_users(users)

    join_channel = data.get("join_channel", "").strip()

    # جوین اجباری فقط زمانی فعال است که join_channel تنظیم شده باشد
    if join_channel:
        joined = check_user_joined_channel(user_id, join_channel)
        if not joined:
            send_message(chat_id, f"لطفا ابتدا در کانال {join_channel} عضو شوید و سپس ادامه دهید.")
            return
        else:
            users[str(user_id)]["joined"] = True
            save_users(users)

    if user_id == ADMIN_ID:
        if text == "/start":
            admin_panel(chat_id)
        elif text.startswith("/setlink "):
            link = text[9:].strip()
            data["config_link"] = link
            save_data(data)
            send_message(chat_id, "لینک کانفیگ تنظیم شد.")
        elif text.startswith("/setchannel "):
            channel = text[12:].strip()
            # بررسی اینکه کانال خالی نباشد و درست تنظیم شود
            if channel:
                data["join_channel"] = channel
                save_data(data)
                send_message(chat_id, f"کانال جوین اجباری تنظیم شد: {channel}")
            else:
                send_message(chat_id, "لطفا یک نام کانال معتبر وارد کنید. مثلاً @YourChannel یا آیدی عددی کانال.")
        elif text.startswith("/setping "):
            try:
                interval = int(text[9:].strip())
                data["ping_interval"] = interval
                save_data(data)
                send_message(chat_id, f"زمان تست مجدد کانفیگ روی {interval} ثانیه تنظیم شد.")
            except:
                send_message(chat_id, "مقدار معتبر نیست.")
        elif text.startswith("/uploadvideo "):
            send_message(chat_id, "جهت ارسال ویدیو آموزشی لطفا فایل را به صورت داکیومنت ارسال کنید.")
        else:
            send_message(chat_id, "دستور ناشناخته.")
    else:
        if text == "/start":
            user_menu(chat_id)
        else:
            send_message(chat_id, "برای استفاده از ربات لطفا از منو استفاده کنید.")

def handle_callback(callback):
    chat_id = callback["message"]["chat"]["id"]
    user_id = callback["from"]["id"]
    data = load_data()

    if user_id == ADMIN_ID:
        data_callback = callback["data"]

        if data_callback == "set_link":
            send_message(chat_id, "لطفا لینک فایل کانفیگ را با دستور زیر ارسال کنید:\n/setlink https://example.com/config.txt")
        elif data_callback == "set_channel":
            send_message(chat_id, "لطفا نام کاربری کانال جوین اجباری را با دستور زیر ارسال کنید:\n/setchannel @YourChannel\nیا آیدی عددی کانال را ارسال کنید.")
        elif data_callback == "set_ping_interval":
            send_message(chat_id, "لطفا زمان تست مجدد کانفیگ به ثانیه را با دستور زیر ارسال کنید:\n/setping 300")
        elif data_callback == "upload_video":
            send_message(chat_id, "لطفا فایل ویدیوی آموزشی را به صورت داکیومنت ارسال کنید و در کپشن پلتفرم را مشخص کنید (android, ios, windows). مثال:\nکپشن: android")
        elif data_callback == "list_videos":
            videos = os.listdir(VIDEOS_DIR)
            if not videos:
                send_message(chat_id, "ویدیویی وجود ندارد.")
                return
            text = "ویدیوهای آموزشی موجود:\n"
            for v in videos:
                text += f"- {v}\n"
            send_message(chat_id, text)
        else:
            send_message(chat_id, "دکمه ناشناخته.")
    else:
        # برای کاربران عادی
        if callback["data"] == "get_healthy_configs":
            # چک لینک کانفیگ
            if "config_link" not in data or not data["config_link"]:
                send_message(chat_id, "کانفیگی تنظیم نشده است.")
                return
            join_channel = data.get("join_channel", "").strip()
            if join_channel:
                if not check_user_joined_channel(user_id, join_channel):
                    send_message(chat_id, f"لطفا ابتدا در کانال {join_channel} عضو شوید.")
                    return

            send_message(chat_id, "در حال دریافت کانفیگ‌ها و تست سلامت آنها، لطفا صبر کنید...")
            filename, hosts = extract_configs_from_link(data["config_link"])
            if not filename or not hosts:
                send_message(chat_id, "خطا در دریافت یا استخراج کانفیگ‌ها.")
                return
            healthy = test_configs(hosts)
            if not healthy:
                send_message(chat_id, "کانفیگ سالم یافت نشد.")
                return
            healthy_text = "\n".join(healthy[:30])  # فقط 30 تا نشان بدهیم
            send_message(chat_id, "کانفیگ‌های سالم:\n" + healthy_text)
        elif callback["data"] == "list_videos":
            videos = os.listdir(VIDEOS_DIR)
            if not videos:
                send_message(chat_id, "ویدیویی وجود ندارد.")
                return
            text = "ویدیوهای آموزشی موجود:\n"
            for v in videos:
                text += f"- {v}\n"
            send_message(chat_id, text)
        else:
            send_message(chat_id, "دکمه ناشناخته.")

def process_update(update):
    if "message" in update:
        handle_message(update["message"])
    elif "callback_query" in update:
        callback = update["callback_query"]
        handle_callback(callback)
        # حتما جواب دادن به callback_query ضروری است:
        telegram_request("answerCallbackQuery", {"callback_query_id": callback["id"]})

def main_loop():
    offset = None
    while True:
        updates = get_updates(offset, timeout=30)
        for update in updates:
            offset = update["update_id"] + 1
            process_update(update)
        time.sleep(1)

if __name__ == "__main__":
    main_loop()
