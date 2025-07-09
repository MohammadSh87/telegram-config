import requests
import json
import os
import time

TOKEN = "8057495132:AAESf8cO_FbIfYC4DTp8uVBKTU_ECNiTznA"
ADMIN_ID = 2075973663  # آیدی ادمین عددی

VIDEOS_DIR = "videos"
DATA_FILE = "data.json"

if not os.path.exists(VIDEOS_DIR):
    os.makedirs(VIDEOS_DIR)

def telegram_request(method, params=None, files=None):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    if files:
        r = requests.post(url, data=params, files=files)
    else:
        r = requests.post(url, data=params)
    try:
        return r.json()
    except:
        return {}

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

def check_user_joined_channel(user_id, channel_username):
    # نمونه: چک کردن عضویت در کانال (برای شروع همیشه True برمیگردونه)
    # برای تست اولیه به سادگی True برگردان
    return True

def admin_keyboard():
    keyboard = {
        "inline_keyboard": [
            [{"text": "تنظیم لینک کانفیگ", "callback_data": "set_link"}],
            [{"text": "تنظیم کانال جوین اجباری", "callback_data": "set_channel"}],
            [{"text": "آپلود ویدیو آموزشی", "callback_data": "upload_video"}],
            [{"text": "لیست ویدیوها", "callback_data": "list_videos"}],
        ]
    }
    return keyboard

def user_keyboard():
    keyboard = {
        "inline_keyboard": [
            [{"text": "دریافت کانفیگ‌های سالم", "callback_data": "get_healthy_configs"}],
            [{"text": "لیست ویدیوها", "callback_data": "list_videos"}],
        ]
    }
    return keyboard

def handle_message(msg):
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    text = msg.get("text", "")

    data = load_data()
    join_channel = data.get("join_channel", "").strip()

    if join_channel and not check_user_joined_channel(user_id, join_channel):
        send_message(chat_id, f"لطفا ابتدا در کانال {join_channel} عضو شوید و سپس ادامه دهید.")
        return

    if user_id == ADMIN_ID:
        if text == "/start":
            send_message(chat_id, "سلام ادمین! به پنل مدیریت خوش آمدید.", admin_keyboard())
        elif text.startswith("/setlink "):
            link = text[9:].strip()
            data["config_link"] = link
            save_data(data)
            send_message(chat_id, "لینک کانفیگ تنظیم شد.")
        elif text.startswith("/setchannel "):
            channel = text[12:].strip()
            if channel.startswith("@"):
                data["join_channel"] = channel
                save_data(data)
                send_message(chat_id, f"کانال جوین اجباری تنظیم شد: {channel}")
            else:
                send_message(chat_id, "لطفا نام کانال را به صورت @channel وارد کنید.")
        else:
            send_message(chat_id, "دستور نامعتبر یا پیام پشتیبانی نشده برای ادمین.")
    else:
        if text == "/start":
            send_message(chat_id, "سلام! به ربات خوش آمدید.", user_keyboard())
        else:
            send_message(chat_id, "برای استفاده از ربات لطفا از دکمه‌ها استفاده کنید.")

def handle_callback(callback):
    chat_id = callback["message"]["chat"]["id"]
    user_id = callback["from"]["id"]
    data = load_data()

    # پاسخ به callback حتما باید داده شود
    telegram_request("answerCallbackQuery", {"callback_query_id": callback["id"]})

    if user_id == ADMIN_ID:
        cd = callback["data"]
        if cd == "set_link":
            send_message(chat_id, "لطفا لینک فایل کانفیگ را با دستور زیر ارسال کنید:\n/setlink https://example.com/config.txt")
        elif cd == "set_channel":
            send_message(chat_id, "لطفا نام کانال جوین اجباری را به صورت @channel با دستور زیر ارسال کنید:\n/setchannel @YourChannel")
        elif cd == "upload_video":
            send_message(chat_id, "لطفا فایل ویدیوی آموزشی را به صورت داکیومنت ارسال کنید.")
        elif cd == "list_videos":
            videos = os.listdir(VIDEOS_DIR)
            if videos:
                text = "ویدیوهای موجود:\n" + "\n".join(videos)
            else:
                text = "هیچ ویدیویی موجود نیست."
            send_message(chat_id, text)
        else:
            send_message(chat_id, "دکمه ناشناخته.")
    else:
        if callback["data"] == "get_healthy_configs":
            if "config_link" not in data or not data["config_link"]:
                send_message(chat_id, "کانفیگ تنظیم نشده است.")
            else:
                send_message(chat_id, "کانفیگ‌ها به زودی ارسال خواهند شد (اینجا می‌توانید تابع دانلود و تست اضافه کنید).")
        elif callback["data"] == "list_videos":
            videos = os.listdir(VIDEOS_DIR)
            if videos:
                text = "ویدیوهای موجود:\n" + "\n".join(videos)
            else:
                text = "هیچ ویدیویی موجود نیست."
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
    file_id = document.get("file_id")
    file_name = document.get("file_name")
    if not file_id or not file_name:
        return

    file_info = telegram_request("getFile", {"file_id": file_id})
    if not file_info.get("ok"):
        send_message(chat_id, "خطا در دریافت اطلاعات فایل.")
        return
    file_path = file_info["result"]["file_path"]
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    r = requests.get(file_url)
    if r.status_code != 200:
        send_message(chat_id, "خطا در دانلود فایل.")
        return

    save_path = os.path.join(VIDEOS_DIR, file_name)
    with open(save_path, "wb") as f:
        f.write(r.content)

    send_message(chat_id, f"فایل '{file_name}' با موفقیت ذخیره شد.")

def main():
    offset = None
    while True:
        try:
            params = {"timeout": 100}
            if offset:
                params["offset"] = offset
            res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params=params, timeout=120)
            data = res.json()
            if not data.get("ok"):
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
            time.sleep(1)

if __name__ == "__main__":
    main()
