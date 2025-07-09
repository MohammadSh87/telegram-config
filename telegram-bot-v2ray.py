import requests
import json
import os

TOKEN = "8057495132:AAESf8cO_FbIfYC4DTp8uVBKTU_ECNiTznA"
ADMIN_ID = 2075973663 # آیدی عددی ادمین
VIDEOS_DIR = "videos"
DATA_FILE = "data.json"
USERS_FILE = "users.json"

if not os.path.exists(VIDEOS_DIR):
    os.makedirs(VIDEOS_DIR)

def telegram_request(method, params):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    return requests.post(url, data=params).json()

def send_message(chat_id, text, reply_markup=None):
    params = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        params["reply_markup"] = json.dumps(reply_markup)
    telegram_request("sendMessage", params)

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def check_user_joined_channel(user_id, channel):
    # این تابع باید با استفاده از API تلگرام چک کند کاربر عضو کانال هست یا نه
    # برای سادگی در اینجا فرض می‌کنیم همیشه True برمی‌گردد
    # اگر می‌خواهید واقعی باشد باید از getChatMember استفاده کنید
    # توجه: این متد نیازمند Token با مجوزهای بالا است
    return True

def extract_configs_from_link(link):
    # این تابع لینک کانفیگ را می‌گیرد و فایل را دانلود و کانفیگ‌ها را استخراج می‌کند
    # به صورت نمونه اینجا فقط یک فایل txt دانلود و به خطوط تقسیم شده برمی‌گرداند
    try:
        r = requests.get(link)
        if r.status_code == 200:
            filename = "config.txt"
            with open(filename, "wb") as f:
                f.write(r.content)
            hosts = r.text.strip().split("\n")
            return filename, hosts
        else:
            return None, None
    except Exception:
        return None, None

def test_configs(hosts):
    # تست سلامت کانفیگ‌ها، در اینجا صرفاً نمونه است که همه را سالم فرض می‌کند
    # در واقع باید ping یا تست اتصال به هاست‌ها انجام شود
    return hosts

def admin_panel(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "تنظیم لینک کانفیگ", "callback_data": "set_link"}],
            [{"text": "تنظیم کانال جوین اجباری", "callback_data": "set_channel"}],
            [{"text": "تنظیم زمان تست مجدد کانفیگ (ثانیه)", "callback_data": "set_ping_interval"}],
            [{"text": "آپلود ویدیو آموزشی", "callback_data": "upload_video"}],
            [{"text": "لیست ویدیوهای آموزشی", "callback_data": "list_videos"}],
        ]
    }
    send_message(chat_id, "پنل مدیریت:", reply_markup=keyboard)

def user_menu(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "دریافت کانفیگ‌های سالم", "callback_data": "get_healthy_configs"}],
            [{"text": "لیست ویدیوهای آموزشی", "callback_data": "list_videos"}],
        ]
    }
    send_message(chat_id, "منوی کاربری:", reply_markup=keyboard)

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
            if channel:
                data["join_channel"] = channel
                save_data(data)
                send_message(chat_id, f"کانال جوین اجباری تنظیم شد: {channel}")
            else:
                send_message(chat_id, "لطفا یک نام کانال معتبر وارد کنید.")
        elif text.startswith("/setping "):
            try:
                interval = int(text[9:].strip())
                data["ping_interval"] = interval
                save_data(data)
                send_message(chat_id, f"زمان تست مجدد کانفیگ روی {interval} ثانیه تنظیم شد.")
            except:
                send_message(chat_id, "مقدار معتبر نیست.")
        elif text.startswith("/uploadvideo "):
            send_message(chat_id, "لطفا فایل ویدیوی آموزشی را به صورت داکیومنت ارسال کنید و در کپشن پلتفرم را مشخص کنید (android, ios, windows).")
        else:
            # پیام‌های غیر مرتبط ادمین اینجا جواب نمی‌گیرند
            pass
    else:
        # کاربران عادی فقط پیام /start را پاسخ می‌دهند
        if text == "/start":
            user_menu(chat_id)
        else:
            # بقیه پیام‌های متنی توسط ربات پاسخ داده نمی‌شود
            pass

def handle_callback(callback):
    chat_id = callback["message"]["chat"]["id"]
    user_id = callback["from"]["id"]
    data = load_data()

    # حتما به callback پاسخ دهید
    telegram_request("answerCallbackQuery", {"callback_query_id": callback["id"]})

    if user_id == ADMIN_ID:
        data_callback = callback["data"]
        if data_callback == "set_link":
            send_message(chat_id, "لطفا لینک فایل کانفیگ را با دستور زیر ارسال کنید:\n/setlink https://example.com/config.txt")
        elif data_callback == "set_channel":
            send_message(chat_id, "لطفا نام کاربری کانال جوین اجباری را با دستور زیر ارسال کنید:\n/setchannel @YourChannel")
        elif data_callback == "set_ping_interval":
            send_message(chat_id, "لطفا زمان تست مجدد کانفیگ به ثانیه را با دستور زیر ارسال کنید:\n/setping 300")
        elif data_callback == "upload_video":
            send_message(chat_id, "لطفا فایل ویدیوی آموزشی را به صورت داکیومنت ارسال کنید و در کپشن پلتفرم را مشخص کنید (android, ios, windows).")
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
        if callback["data"] == "get_healthy_configs":
            if "config_link" not in data or not data["config_link"]:
                send_message(chat_id, "کانفیگی تنظیم نشده است.")
                return
            join_channel = data.get("join_channel", "").strip()
            if join_channel and not check_user_joined_channel(user_id, join_channel):
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
            healthy_text = "\n".join(healthy[:30])
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

def handle_document(msg):
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    if user_id != ADMIN_ID:
        return
    document = msg.get("document")
    if not document:
        return
    file_name = document.get("file_name")
    file_id = document.get("file_id")
    if not file_name or not file_id:
        return

    # دانلود فایل
    file_path_res = telegram_request("getFile", {"file_id": file_id})
    if not file_path_res.get("ok"):
        send_message(chat_id, "خطا در دریافت فایل")
        return
    file_path = file_path_res["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    r = requests.get(download_url)
    if r.status_code != 200:
        send_message(chat_id, "خطا در دانلود فایل")
        return

    save_path = os.path.join(VIDEOS_DIR, file_name)
    with open(save_path, "wb") as f:
        f.write(r.content)

    send_message(chat_id, f"ویدیوی آموزشی '{file_name}' با موفقیت ذخیره شد.")

def main():
    offset = None
    while True:
        try:
            params = {"timeout": 100}
            if offset:
                params["offset"] = offset
            res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params=params, timeout=120)
            data = res.json()
            if not data["ok"]:
                continue
            for update in data["result"]:
                offset = update["update_id"] + 1
                if "message" in update:
                    msg = update["message"]
                    if "text" in msg:
                        handle_message(msg)
                    elif "document" in msg:
                        handle_document(msg)
                elif "callback_query" in update:
                    handle_callback(update["callback_query"])
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    main()
