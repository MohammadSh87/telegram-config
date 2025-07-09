import requests
import time
import os
import socket
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
    "join_channel_username": "",
    "join_channel_chat_id": None
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

def ping_host(host, port=443, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except:
        return False

def test_links_and_send(chat_id):
    if not data["config_url"]:
        send_message(chat_id, "❌ لینک کانفیگ تنظیم نشده است.")
        return

    urls = [u.strip() for u in data["config_url"].splitlines() if u.strip()]
    if not urls:
        send_message(chat_id, "❌ هیچ لینکی تنظیم نشده است.")
        return

    keyboard = [[{"text": f"📄 فایل {i+1}", "callback_data": f"cfg_{i}"}] for i in range(len(urls))]
    reply_markup = {"inline_keyboard": keyboard}
    send_message(chat_id, "✅ فایل مورد نظر را انتخاب کنید:", reply_markup=reply_markup)

def process_selected_config(chat_id, index):
    urls = [u.strip() for u in data["config_url"].splitlines() if u.strip()]
    if index >= len(urls):
        send_message(chat_id, "❌ فایل انتخابی وجود ندارد.")
        return

    url = urls[index]
    send_message(chat_id, f"⏳ در حال دریافت و تست فایل {index+1}...")

    try:
        response = requests.get(url, timeout=10)
        content = response.text
    except:
        send_message(chat_id, "❌ دریافت فایل با خطا مواجه شد.")
        return

    lines = content.strip().splitlines()
    valid_links = []

    for link in lines:
        link = link.strip()
        if not link:
            continue
        if any(link.startswith(proto) for proto in ["vmess://", "vless://", "trojan://", "ss://", "ssr://"]):
            # برای پینگ لینک‌ها، از آدرس سرور استفاده می‌کنیم
            try:
                raw = link.split("@")[-1].split(":")[0]
                if raw and ping_host(raw):
                    valid_links.append(link)
            except:
                continue
        elif link.startswith("http"):
            try:
                r = requests.get(link, timeout=3)
                if r.status_code == 200:
                    valid_links.append(link)
            except:
                continue

    if not valid_links:
        send_message(chat_id, "❌ هیچ کانفیگ سالمی پیدا نشد.")
        return

    filename = f"valid_config_{chat_id}_{index+1}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(valid_links))

    caption = f"🕒 تست شده در: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n📄 فایل {index+1}\n✅ لینک‌های سالم: {len(valid_links)}"
    send_document(chat_id, filename, caption=caption)
    os.remove(filename)

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
            callback = update.get("callback_query")

            if callback:
                data_callback = callback["data"]
                chat_id = callback["message"]["chat"]["id"]
                user_id = callback["from"]["id"]
                if data_callback.startswith("cfg_"):
                    index = int(data_callback.replace("cfg_", ""))
                    process_selected_config(chat_id, index)
                continue

            if not message:
                continue

            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            user_id = message["from"]["id"]
            is_admin = (user_id == ADMIN_ID)

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
                    send_message(chat_id, "✅ لینک‌ها ذخیره شدند.")
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
                        send_message(chat_id, "❌ دریافت chat_id کانال موفق نبود.")
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
                platform = {"📱 Android": "android", "🍏 iOS": "ios", "💻 Windows": "windows"}[text]
                file_id = data["videos"].get(platform)
                if file_id:
                    requests.post(f"{API_URL}/sendVideo", json={
                        "chat_id": chat_id,
                        "video": file_id,
                        "caption": f"🎬 آموزش برای {platform.title()}",
                        "parse_mode": "HTML"
                    })
                else:
                    send_message(chat_id, f"❌ آموزشی برای {platform.title()} موجود نیست.")

            elif text == "🔗 تنظیم لینک کانفیگ" and is_admin:
                state[chat_id] = "set_config_url"
                send_message(chat_id, "لطفاً لینک/لینک‌های فایل‌های کانفیگ را ارسال کنید (هر لینک در یک خط):")

            elif text == "⏱ تنظیم فاصله تست خودکار" and is_admin:
                state[chat_id] = "set_test_interval"
                send_message(chat_id, "لطفاً فاصله زمانی تست خودکار (بر حسب دقیقه) را وارد کنید:")

            elif text == "⚙ تنظیم لینک کانال (جوین اجباری)" and is_admin:
                state[chat_id] = "set_channel_link"
                send_message(chat_id, "لطفاً آیدی کانال (با @) را وارد کنید:")

            elif text == "🔙 بازگشت به پنل مدیریت" and is_admin:
                admin_panel(chat_id)

            elif text == "🔙 بازگشت به پنل کاربر":
                user_panel(chat_id)

if __name__ == "__main__":
    main()

