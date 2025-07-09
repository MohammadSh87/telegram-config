import requests
import time
import os
from datetime import datetime
import json

TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
ADMIN_ID = 123456789  # آیدی عددی ادمین

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
    "join_channel_username": "",
    "join_channel_chat_id": None
}


def get_updates():
    global OFFSET
    try:
        response = requests.get(f"{API_URL}/getUpdates", params={"offset": OFFSET + 1, "timeout": 5})
        result = response.json()
        if result.get("ok"):
            return result["result"]
    except:
        pass
    return []


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{API_URL}/sendMessage", json=payload)


def send_document(chat_id, file_path):
    with open(file_path, 'rb') as f:
        requests.post(f"{API_URL}/sendDocument", files={"document": f}, data={"chat_id": chat_id})


def test_links_and_send(chat_id):
    send_message(chat_id, "⏳ در حال دریافت و تست لینک‌ها...")

    url = data["config_url"]
    try:
        response = requests.get(url, timeout=10)
        content = response.text
    except:
        send_message(chat_id, "❌ دریافت فایل کانفیگ با خطا مواجه شد.")
        return

    lines = content.strip().splitlines()
    valid_links = []
    total = len(lines)

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
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(valid_links))
        f.write(f"\n\n🕒 تست شده در: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    send_document(chat_id, filename)
    os.remove(filename)


def set_channel_chat_id():
    username = data["join_channel_username"]
    if not username:
        return False
    if username.startswith("@"):
        username = username[1:]
    try:
        resp = requests.get(f"{API_URL}/getChat", params={"chat_id": username}, timeout=5)
        result = resp.json()
        if result.get("ok"):
            data["join_channel_chat_id"] = result["result"]["id"]
            return True
    except:
        pass
    return False


def check_join_channel(user_id):
    if data["join_channel_chat_id"] is None:
        if not set_channel_chat_id():
            return True  # اگر نشد، فعلاً عبور بده

    try:
        resp = requests.get(f"{API_URL}/getChatMember", params={
            "chat_id": data["join_channel_chat_id"],
            "user_id": user_id
        }, timeout=5)
        result = resp.json()
        if result.get("ok"):
            status = result["result"]["status"]
            return status in ["member", "administrator", "creator"]
    except:
        pass
    return False


def admin_panel(chat_id):
    markup = {
        "keyboard": [
            ["🔗 تنظیم لینک کانفیگ", "📥 تست دستی کانفیگ"],
            ["📤 ارسال آموزش"],
            ["⏱ تنظیم فاصله تست خودکار"],
            ["⚙ تنظیم لینک کانال (جوین اجباری)"]
        ],
        "resize_keyboard": True
    }
    send_message(chat_id, "🔧 پنل مدیریت", reply_markup=markup)


def user_panel(chat_id):
    markup = {
        "keyboard": [
            ["📥 دریافت کانفیگ سالم"],
            ["🎥 دریافت آموزش"]
        ],
        "resize_keyboard": True
    }
    send_message(chat_id, "به ربات خوش آمدید!", reply_markup=markup)


def main():
    global OFFSET
    print("ربات تلگرام فعال شد...")
    while True:
        updates = get_updates()
        for update in updates:
            OFFSET = update["update_id"]
            msg = update.get("message")
            if not msg:
                continue

            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")
            user_id = msg["from"]["id"]
            is_admin = (user_id == ADMIN_ID)

            if not is_admin and data["join_channel_username"]:
                if not check_join_channel(user_id):
                    send_message(chat_id,
                        f"❗ لطفاً ابتدا عضو کانال شوید: {data['join_channel_username']}\nسپس /start را بفرستید.")
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
                        send_message(chat_id, "❌ مقدار نامعتبر است.")
                elif action == "set_channel_link" and is_admin:
                    data["join_channel_username"] = text.strip()
                    data["join_channel_chat_id"] = None
                    if set_channel_chat_id():
                        send_message(chat_id, f"✅ لینک کانال ذخیره شد: {data['join_channel_chat_id']}")
                    else:
                        send_message(chat_id, "❌ دریافت chat_id ناموفق بود.")
                elif action.startswith("upload_video_") and is_admin:
                    platform = action.split("_")[-1]
                    video = msg.get("video")
                    if video:
                        file_id = video["file_id"]
                        data["videos"][platform] = file_id
                        send_message(chat_id, f"✅ ویدیوی {platform} ذخیره شد.")
                    else:
                        send_message(chat_id, "❌ فایل ویدیویی پیدا نشد.")
                continue

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
                    "resize_keyboard": True
                }
                send_message(chat_id, "لطفاً پلتفرم را انتخاب کنید:", reply_markup=markup)

            elif text == "📤 ارسال آموزش" and is_admin:
                markup = {
                    "keyboard": [
                        ["آپلود Android", "آپلود iOS"],
                        ["آپلود Windows"],
                        ["🔙 بازگشت به پنل مدیریت"]
                    ],
                    "resize_keyboard": True
                }
                send_message(chat_id, "پلتفرم موردنظر برای آپلود:", reply_markup=markup)

            elif text.startswith("آپلود ") and is_admin:
                platform = text.split(" ")[1].lower()
                state[chat_id] = f"upload_video_{platform}"
                send_message(chat_id, f"لطفاً ویدیوی {platform} را ارسال کنید:")

            elif text in ["📱 Android", "🍏 iOS", "💻 Windows"]:
                platform = text.split()[1].lower()
                file_id = data["videos"].get(platform)
                if file_id:
                    # ارسال ویدیو از طریق file_id
                    requests.post(f"{API_URL}/sendVideo", data={
                        "chat_id": chat_id,
                        "video": file_id
                    })
                else:
                    send_message(chat_id, f"❌ ویدیوی {platform} موجود نیست.")

            elif text == "🔗 تنظیم لینک کانفیگ" and is_admin:
                state[chat_id] = "set_config_url"
                send_message(chat_id, "لینک فایل کانفیگ را ارسال کنید:")

            elif text == "⏱ تنظیم فاصله تست خودکار" and is_admin:
                state[chat_id] = "set_test_interval"
                send_message(chat_id, "عدد فاصله تست (دقیقه) را وارد کنید:")

            elif text == "⚙ تنظیم لینک کانال (جوین اجباری)" and is_admin:
                state[chat_id] = "set_channel_link"
                send_message(chat_id, "آیدی کانال را به صورت @channel وارد کنید:")

            elif text == "🔙 بازگشت به پنل کاربر":
                user_panel(chat_id)

            elif text == "🔙 بازگشت به پنل مدیریت" and is_admin:
                admin_panel(chat_id)

            else:
                send_message(chat_id, "دستور نامعتبر است.")

        time.sleep(1)


if __name__ == "__main__":
    main()
