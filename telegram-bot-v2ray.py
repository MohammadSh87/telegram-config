import requests
import time
import os
from datetime import datetime
import json
import threading

TOKEN = "8057495132:AAESf8cO_FbIfYC4DTp8uVBKTU_ECNiTznA"
ADMIN_ID = 7089528908

API_URL = f"https://api.telegram.org/bot{TOKEN}"
OFFSET = 0

state = {}
data = {
    "config_url": "",
    "auto_test_interval": 0,  # دقیقه
    "videos": {
        "android": None,
        "ios": None,
        "windows": None
    },
    "join_channel_username": "",  # به صورت @channelusername
    "join_channel_chat_id": None,  # chat_id واقعی کانال
    "last_valid_config_file": None,  # مسیر فایل ذخیره شده آخرین کانفیگ سالم
    "last_test_time": None  # زمان آخرین تست به صورت datetime
}

lock = threading.Lock()

def get_updates():
    global OFFSET
    try:
        resp = requests.get(f"{API_URL}/getUpdates", params={"offset": OFFSET + 1, "timeout": 10})
        result = resp.json()
        if result.get("ok"):
            return result["result"]
    except Exception as e:
        print("Error in get_updates:", e)
    return []

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(f"{API_URL}/sendMessage", json=payload)
    except Exception as e:
        print("Error in send_message:", e)

def send_document(chat_id, file_path, caption=None):
    try:
        with open(file_path, 'rb') as f:
            data_send = {"chat_id": chat_id}
            if caption:
                data_send["caption"] = caption
                data_send["parse_mode"] = "HTML"
            requests.post(f"{API_URL}/sendDocument", files={"document": f}, data=data_send)
    except Exception as e:
        print("Error in send_document:", e)

def set_channel_chat_id():
    username = data["join_channel_username"]
    if not username:
        return False
    if username.startswith("@"):
        username = username[1:]
    try:
        resp = requests.get(f"{API_URL}/getChat", params={"chat_id": f"@{username}"}, timeout=5)
        result = resp.json()
        if result.get("ok"):
            chat_id = result["result"]["id"]
            data["join_channel_chat_id"] = chat_id
            return True
    except Exception as e:
        print("خطا در دریافت chat_id کانال:", e)
    return False

def check_join_channel(user_id):
    if data["join_channel_chat_id"] is None:
        if not set_channel_chat_id():
            # اگر chat_id کانال مشخص نبود، پیش‌فرض اجازه می‌دهیم
            return True

    channel_chat_id = data["join_channel_chat_id"]
    try:
        resp = requests.get(f"{API_URL}/getChatMember", params={
            "chat_id": channel_chat_id,
            "user_id": user_id
        }, timeout=5)
        result = resp.json()
        if result.get("ok"):
            status = result["result"]["status"]
            if status in ["member", "administrator", "creator"]:
                return True
    except:
        pass
    return False

def test_links_and_save():
    """
    تست لینک‌ها، ذخیره لینک‌های سالم در فایل و آپدیت زمان تست.
    بدون ارسال به کاربر (برای تست خودکار).
    """
    url = data["config_url"]
    if not url:
        return False, "لینک کانفیگ تنظیم نشده است."

    try:
        response = requests.get(url, timeout=10)
        content = response.text
    except Exception:
        return False, "دریافت فایل با خطا مواجه شد."

    lines = content.strip().splitlines()
    valid_links = []
    for link in lines:
        link = link.strip()
        if not link:
            continue
        try:
            if link.startswith("http"):
                r = requests.get(link, timeout=3)
                if r.status_code == 200:
                    valid_links.append(link)
            elif any(link.startswith(proto) for proto in ["vmess://", "vless://", "ss://", "trojan://", "ssr://"]):
                valid_links.append(link)
        except:
            pass

    if not valid_links:
        return False, "هیچ لینکی سالم نبود."

    filename = "valid_config.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(valid_links))

    with lock:
        data["last_valid_config_file"] = filename
        data["last_test_time"] = datetime.now()

    return True, "تست لینک‌ها موفق بود."

def send_valid_config(chat_id):
    with lock:
        filename = data["last_valid_config_file"]
        last_test_time = data["last_test_time"]

    if not filename or not os.path.exists(filename):
        send_message(chat_id, "❌ هنوز هیچ کانفیگ سالمی موجود نیست. لطفاً چند لحظه دیگر تلاش کنید.")
        return

    caption = ""
    if last_test_time:
        caption = f"🕒 زمان آخرین تست: {last_test_time.strftime('%Y-%m-%d %H:%M:%S')}"
    send_document(chat_id, filename, caption=caption)

def auto_test_worker():
    """
    اجرای تست خودکار دوره‌ای بر اساس زمان تعیین شده توسط ادمین.
    """
    while True:
        interval = data.get("auto_test_interval", 0)
        if interval > 0:
            success, msg = test_links_and_save()
            if success:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] تست خودکار موفق بود.")
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] خطا در تست خودکار: {msg}")
            time.sleep(interval * 60)
        else:
            time.sleep(10)  # اگر زمان تست صفر است، هر 10 ثانیه چک کن

def admin_panel(chat_id):
    markup = {
        "keyboard": [
            ["🔗 تنظیم لینک کانفیگ", "📥 دریافت کانفیگ سالم"],
            ["📤 ارسال آموزش"],
            ["⏱ تنظیم فاصله تست خودکار"],
            ["⚙ تنظیم لینک کانال (جوین اجباری)"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    send_message(chat_id, "🔧 پنل مدیریت", reply_markup=markup)

def user_panel(chat_id):
    markup = {
        "keyboard": [
            ["📥 دریافت کانفیگ سالم"],
            ["🎥 دریافت آموزش"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    send_message(chat_id, "به ربات خوش آمدید!", reply_markup=markup)

def main():
    global OFFSET
    print("ربات فعال شد...")

    # اجرای تست خودکار در یک Thread جدا
    threading.Thread(target=auto_test_worker, daemon=True).start()

    while True:
        updates = get_updates()
        for update in updates:
            OFFSET = update["update_id"]
            message = update.get("message")
            if not message:
                continue

            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            user_id = message["from"]["id"]
            is_admin = (user_id == ADMIN_ID)

            # جوین اجباری اگر فعال و کاربر عادی
            if not is_admin and data.get("join_channel_username"):
                if not check_join_channel(user_id):
                    send_message(chat_id,
                        f"❗ لطفاً ابتدا عضو کانال ما شوید: {data['join_channel_username']}\n"
                        "پس از عضویت پیام /start را ارسال کنید.")
                    continue

            if chat_id in state:
                action = state.pop(chat_id)
                if action == "set_config_url" and is_admin:
                    data["config_url"] = text.strip()
                    send_message(chat_id, "✅ لینک ذخیره شد.")

                elif action == "set_test_interval" and is_admin:
                    try:
                        interval = int(text)
                        data["auto_test_interval"] = interval
                        send_message(chat_id, f"✅ فاصله تست ذخیره شد: {interval} دقیقه")
                    except:
                        send_message(chat_id, "❌ عدد معتبر نیست.")

                elif action == "set_channel_link" and is_admin:
                    data["join_channel_username"] = text.strip()
                    data["join_channel_chat_id"] = None
                    if set_channel_chat_id():
                        send_message(chat_id, f"✅ لینک کانال ذخیره و chat_id گرفته شد: {data['join_channel_chat_id']}")
                    else:
                        send_message(chat_id, "❌ دریافت chat_id کانال موفق نبود. لطفاً آیدی را صحیح وارد کنید.")

                elif action.startswith("upload_video_") and is_admin:
                    platform = action.split("_")[-1]
                    video = message.get("video")
                    if video:
                        file_id = video["file_id"]
                        data["videos"][platform] = file_id
                        send_message(chat_id, f"✅ ویدیوی {platform} ذخیره شد.")
                    else:
                        send_message(chat_id, "❌ لطفاً یک ویدیوی معتبر ارسال کنید.")

                else:
                    send_message(chat_id, "❌ دستور نامشخص.")

                continue

            # دستورات اصلی
            if text == "/start":
                if is_admin:
                    admin_panel(chat_id)
                else:
                    user_panel(chat_id)

            elif text == "🔗 تنظیم لینک کانفیگ" and is_admin:
                send_message(chat_id, "لطفاً لینک کانفیگ را ارسال کنید:")
                state[chat_id] = "set_config_url"

            elif text == "⏱ تنظیم فاصله تست خودکار" and is_admin:
                send_message(chat_id, "فاصله زمانی تست خودکار (به دقیقه) را وارد کنید (۰ برای غیرفعال کردن):")
                state[chat_id] = "set_test_interval"

            elif text == "⚙ تنظیم لینک کانال (جوین اجباری)" and is_admin:
                send_message(chat_id, "آیدی کانال را به صورت @channelusername ارسال کنید:")
                state[chat_id] = "set_channel_link"

            elif text == "📥 دریافت کانفیگ سالم":
                send_valid_config(chat_id)

            elif text == "📤 ارسال آموزش" and is_admin:
                markup = {
                    "keyboard": [
                        ["آموزش اندروید", "آموزش iOS", "آموزش ویندوز"],
                        ["بازگشت"]
                    ],
                    "resize_keyboard": True,
                    "one_time_keyboard": True
                }
                send_message(chat_id, "لطفاً آموزش مورد نظر را انتخاب کنید:", reply_markup=markup)

            elif text in ["آموزش اندروید", "آموزش iOS", "آموزش ویندوز"] and is_admin:
                platform = text.split()[-1].lower()
                file_id = data["videos"].get(platform)
                if file_id:
                    # ارسال ویدیو از file_id
                    payload = {
                        "chat_id": chat_id,
                        "video": file_id,
                        "caption": f"ویدیوی آموزش {platform}",
                        "parse_mode": "HTML"
                    }
                    requests.post(f"{API_URL}/sendVideo", data=payload)
                else:
                    send_message(chat_id, f"❌ ویدیویی برای {platform} ثبت نشده است.")

            elif text == "بازگشت" and is_admin:
                admin_panel(chat_id)

            else:
                send_message(chat_id, "دستور نامشخص یا مجاز نیست.")

if __name__ == "__main__":
    main()
