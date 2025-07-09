import requests
import time
import json
import os
import threading
import subprocess

TOKEN = "8057495132:AAESf8cO_FbIfYC4DTp8uVBKTU_ECNiTznA"
ADMIN_ID = 2075973663
API_URL = f'https://api.telegram.org/bot{TOKEN}'  # توسط شما تنظیم شود
JOIN_CHANNEL = ""  # توسط ادمین در پنل تنظیم می‌شود

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

def check_user_joined_channel(user_id, channel_username):
    try:
        res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={channel_username}&user_id={user_id}").json()
        if res["ok"]:
            status = res["result"]["status"]
            return status in ["member", "creator", "administrator"]
    except:
        pass
    return False

def ping_host(host):
    try:
        # پینگ ۱ بار با تایم اوت ۱ ثانیه
        completed = subprocess.run(["ping", "-c", "1", "-W", "1", host], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return completed.returncode == 0
    except:
        return False

def extract_configs_from_link(link):
    # فرض بر این است لینک فایل متنی یا json کانفیگ‌هاست که باید دانلود و ذخیره شود
    try:
        r = requests.get(link, timeout=10)
        if r.status_code == 200:
            filename = os.path.join(CONFIGS_DIR, f"{int(time.time())}.conf")
            with open(filename, "wb") as f:
                f.write(r.content)
            # استخراج هاست‌ها از محتوا (مثال ساده: فرض هر خط یک هاست)
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
    data = load_data()
    buttons = [
        [{"text": "تنظیم لینک کانفیگ", "callback_data": "set_link"}],
        [{"text": "تنظیم کانال جوین اجباری", "callback_data": "set_channel"}],
        [{"text": "آپلود ویدیو آموزشی", "callback_data": "upload_video"}],
        [{"text": "تنظیم زمان تست مجدد کانفیگ", "callback_data": "set_ping_interval"}],
        [{"text": "نمایش ویدیوهای آموزشی", "callback_data": "list_videos"}]
    ]
    send_message(chat_id, "پنل ادمین:", {"inline_keyboard": buttons})

def user_menu(chat_id):
    data = load_data()
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

    # بررسی جوین اجباری
    join_channel = data.get("join_channel", "")
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
            data["join_channel"] = channel
            save_data(data)
            send_message(chat_id, "کانال جوین اجباری تنظیم شد.")
        elif text.startswith("/setping "):
            try:
                interval = int(text[9:].strip())
                data["ping_interval"] = interval
                save_data(data)
                send_message(chat_id, f"زمان تست مجدد کانفیگ روی {interval} ثانیه تنظیم شد.")
            except:
                send_message(chat_id, "مقدار معتبر نیست.")
        elif text.startswith("/uploadvideo "):
            # اینجا باید فایل ویدیو رو ارسال کنه (نیاز به upload جداگانه)
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
            send_message(chat_id, "لطفا نام کاربری کانال جوین اجباری را با دستور زیر ارسال کنید:\n/setchannel @YourChannel")
        elif data_callback == "set_ping_interval":
            send_message(chat_id, "لطفا زمان تست مجدد کانفیگ به ثانیه را با دستور زیر ارسال کنید:\n/setping 300")
        elif data_callback == "upload_video":
            send_message(chat_id, "لطفا فایل ویدیوی آموزشی را به صورت داکیومنت ارسال کنید و در کپشن پلتفرم را مشخص کنید (android, ios, windows). مثال:\nکپشن: android")
        elif data_callback == "list_videos":
            videos = os.listdir(VIDEOS_DIR)
            if not videos:
                send_message(chat_id, "هیچ ویدیویی موجود نیست.")
                return
            text = "ویدیوهای آموزشی موجود:\n"
            for v in videos:
                platform = v.split("_")[0]
                text += f"- {platform}: {v}\n"
            send_message(chat_id, text)
        elif data_callback == "get_healthy_configs":
            if "config_link" not in data:
                send_message(chat_id, "کانفیگی تنظیم نشده است.")
                return
            link = data["config_link"]
            filename, hosts = extract_configs_from_link(link)
            if not hosts:
                send_message(chat_id, "کانفیگ معتبر نیست یا هاست یافت نشد.")
                return
            healthy = test_configs(hosts)
            if not healthy:
                send_message(chat_id, "هیچ هاست سالمی یافت نشد.")
                return
            # ارسال فایل کانفیگ اصلی فقط با هاست‌های سالم اصلاح شده
            content = []
            for h in healthy:
                content.append(h)
            healthy_filename = os.path.join(CONFIGS_DIR, f"healthy_{int(time.time())}.conf")
            with open(healthy_filename, "w") as f:
                f.write("\n".join(content))
            send_document(chat_id, healthy_filename, "کانفیگ‌های سالم:")
        else:
            send_message(chat_id, "گزینه نامعتبر.")
    else:
        if callback["data"] == "get_healthy_configs":
            if "config_link" not in data:
                send_message(chat_id, "کانفیگی تنظیم نشده است.")
                return
            # بررسی عضویت
            join_channel = data.get("join_channel", "")
            if join_channel and not check_user_joined_channel(user_id, join_channel):
                send_message(chat_id, f"لطفا ابتدا در کانال {join_channel} عضو شوید.")
                return
            link = data["config_link"]
            filename, hosts = extract_configs_from_link(link)
            if not hosts:
                send_message(chat_id, "کانفیگ معتبر نیست یا هاست یافت نشد.")
                return
            healthy = test_configs(hosts)
            if not healthy:
                send_message(chat_id, "هیچ هاست سالمی یافت نشد.")
                return
            content = []
            for h in healthy:
                content.append(h)
            healthy_filename = os.path.join(CONFIGS_DIR, f"healthy_{int(time.time())}.conf")
            with open(healthy_filename, "w") as f:
                f.write("\n".join(content))
            send_document(chat_id, healthy_filename, "کانفیگ‌های سالم:")
        elif callback["data"] == "list_videos":
            videos = os.listdir(VIDEOS_DIR)
            if not videos:
                send_message(chat_id, "هیچ ویدیویی موجود نیست.")
                return
            text = "ویدیوهای آموزشی موجود:\n"
            for v in videos:
                platform = v.split("_")[0]
                text += f"- {platform}: {v}\n"
            send_message(chat_id, text)
        else:
            send_message(chat_id, "گزینه نامعتبر.")

def handle_document(msg):
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    if "document" not in msg:
        send_message(chat_id, "فایل ارسال نشده است.")
        return
    file_id = msg["document"]["file_id"]
    file_name = msg["document"].get("file_name", "file")
    caption = msg.get("caption", "").lower().strip()

    # دانلود فایل
    res = telegram_request("getFile", {"file_id": file_id})
    if not res["ok"]:
        send_message(chat_id, "دانلود فایل امکان‌پذیر نیست.")
        return
    file_path = res["result"]["file_path"]
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    r = requests.get(file_url)
    if r.status_code != 200:
        send_message(chat_id, "خطا در دریافت فایل.")
        return

    # ذخیره فایل
    if user_id == ADMIN_ID:
        # آپلود ویدیو
        if caption in ["android", "ios", "windows"]:
            fname = f"{caption}_{int(time.time())}_{file_name}"
            save_path = os.path.join(VIDEOS_DIR, fname)
            with open(save_path, "wb") as f:
                f.write(r.content)
            send_message(chat_id, f"ویدیوی آموزشی برای {caption} ذخیره شد.")
        else:
            # فرض آپلود کانفیگ نیست از طریق فایل داکیومنت
            send_message(chat_id, "کپشن پلتفرم (android, ios, windows) را در هنگام ارسال ویدیو وارد کنید.")
    else:
        send_message(chat_id, "شما اجازه ارسال فایل ندارید.")

def main():
    global TOKEN, API_URL
    # توکن را اینجا قرار دهید یا از جای دیگر بخوانید
    TOKEN = "YOUR_BOT_TOKEN"
    API_URL = f"https://api.telegram.org/bot{TOKEN}/"

    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            if "message" in update:
                msg = update["message"]
                if "text" in msg:
                    handle_message(msg)
                elif "document" in msg:
                    handle_document(msg)
            elif "callback_query" in update:
                handle_callback(update["callback_query"])
        time.sleep(1)

if __name__ == "__main__":
    main()
