import requests
import time
import os
from datetime import datetime
import json

TOKEN = "8057495132:AAESf8cO_FbIfYC4DTp8uVBKTU_ECNiTznA"
ADMIN_ID = 7089528908

API_URL = f"https://api.telegram.org/bot{TOKEN}"
OFFSET = 0

state = {}
data = {
    "config_url": "",
    "auto_test_interval": 0,
    "videos": {
        "android": None,
        "ios": None,
        "windows": None
    },
    "join_channel_username": "",  # به صورت @channelusername
    "join_channel_chat_id": None  # chat_id واقعی کانال بعد از گرفتن
}

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

def test_links_and_send(chat_id):
    send_message(chat_id, "⏳ در حال دریافت و تست لینک‌ها...")
    url = data["config_url"]
    if not url:
        send_message(chat_id, "❌ لینک کانفیگ تنظیم نشده است.")
        return

    try:
        response = requests.get(url, timeout=10)
        content = response.text
    except Exception:
        send_message(chat_id, "❌ دریافت فایل با خطا مواجه شد.")
        return

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
        send_message(chat_id, "❌ هیچ لینکی سالم نبود.")
        return

    filename = f"valid_config_{chat_id}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(valid_links))

    caption = f"🕒 تست شده در: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n⏱ فاصله تست خودکار: {data['auto_test_interval']} دقیقه"
    send_document(chat_id, filename, caption=caption)
    os.remove(filename)

def set_channel_chat_id():
    """
    با استفاده از join_channel_username که به شکل @channelusername است،
    chat_id واقعی کانال را می‌گیرد و ذخیره می‌کند.
    """
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
    """
    بررسی می‌کند کاربر عضو کانال است یا خیر با استفاده از chat_id کانال ذخیره شده.
    اگر join_channel_chat_id وجود نداشته باشد تلاش می‌کند آن را دریافت کند.
    """
    if data["join_channel_chat_id"] is None:
        if not set_channel_chat_id():
            # اگر chat_id کانال مشخص نبود، به عنوان پیش‌فرض اجازه می‌دهیم
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

            # اگر کاربر عادی است و جوین اجباری فعال است
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
                    data["join_channel_chat_id"] = None  # هر بار باید دوباره chat_id گرفته شود
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
                        send_message(chat_id, f"✅ ویدیو {platform} ذخیره شد.")
                    else:
                        send_message(chat_id, "❌ فایل ویدیویی پیدا نشد.")
                continue

            # دستورات عمومی
            if text == "/start":
                if is_admin:
                    admin_panel(chat_id)
                else:
                    user_panel(chat_id)

            elif text == "📥 دریافت کانفیگ سالم":
                test_links_and_send(chat_id)

            elif text == "🎥 دریافت آموزش":
                markup = {
                    "keyboard": [
                        ["📱 Android", "🍏 iOS"],
                        ["💻 Windows"],
                        ["🔙 بازگشت به پنل کاربر"]
                    ],
                    "resize_keyboard": True,
                    "one_time_keyboard": False
                }
                send_message(chat_id, "لطفاً پلتفرم مورد نظر را انتخاب کنید:", reply_markup=markup)

            elif text == "📤 ارسال آموزش" and is_admin:
                markup = {
                    "keyboard": [
                        ["آپلود Android", "آپلود iOS"],
                        ["آپلود Windows"],
                        ["🔙 بازگشت به پنل مدیریت"]
                    ],
                    "resize_keyboard": True,
                    "one_time_keyboard": False
                }
                send_message(chat_id, "پلتفرم برای آپلود آموزش:", reply_markup=markup)

            elif text.startswith("آپلود ") and is_admin:
                platform = text.split(" ")[1].lower()
                state[chat_id] = f"upload_video_{platform}"
                send_message(chat_id, f"لطفاً فایل ویدیویی {platform} را ارسال کنید:")

            elif text in ["📱 Android", "🍏 iOS", "💻 Windows"]:
                # استخراج platform از متن (مثلاً "📱 Android" => "android")
                if text == "📱 Android":
                    platform = "android"
                elif text == "🍏 iOS":
                    platform = "ios"
                elif text == "💻 Windows":
                    platform = "windows"
                else:
                    platform = None

                if platform:
                    file_id = data["videos"].get(platform)
                    if file_id:
                        try:
                            # ارسال ویدیو از روی file_id
                            payload = {
                                "chat_id": chat_id,
                                "video": file_id
                            }
                            resp = requests.post(f"{API_URL}/sendVideo", json=payload)
                            if not resp.json().get("ok"):
                                send_message(chat_id, f"خطا در ارسال ویدیو {platform}.")
                        except Exception as e:
                            send_message(chat_id, f"خطا در ارسال ویدیو {platform}.")
                    else:
                        send_message(chat_id, f"🚫 ویدیوی آموزش {platform} ذخیره نشده است.")
                else:
                    send_message(chat_id, "❌ پلتفرم نامعتبر است.")

            elif text == "🔙 بازگشت به پنل کاربر":
                user_panel(chat_id)

            elif text == "🔙 بازگشت به پنل مدیریت" and is_admin:
                admin_panel(chat_id)

            elif text == "🔗 تنظیم لینک کانفیگ" and is_admin:
                state[chat_id] = "set_config_url"
                send_message(chat_id, "لطفاً لینک کانفیگ را ارسال کنید:")

            elif text == "⏱ تنظیم فاصله تست خودکار" and is_admin:
                state[chat_id] = "set_test_interval"
                send_message(chat_id, "لطفاً فاصله تست خودکار را (بر حسب دقیقه) ارسال کنید:")

            elif text == "⚙ تنظیم لینک کانال (جوین اجباری)" and is_admin:
                state[chat_id] = "set_channel_link"
                send_message(chat_id, "لطفاً لینک کانال را با @ وارد کنید (مثلاً @channelusername):")

            else:
                send_message(chat_id, "دستور ناشناخته یا دسترسی ندارید.")

        time.sleep(1)

if __name__ == "__main__":
    main()
