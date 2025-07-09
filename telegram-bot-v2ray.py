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
    "config_urls": {},  # دیکشنری برای ذخیره چندین لینک با نام‌های مختلف
    "auto_test_interval": 0,
    "videos": {
        "android": None,
        "ios": None,
        "windows": None
    },
    "join_channel_username": "",
    "join_channel_chat_id": None
}

# بارگذاری داده‌ها از فایل JSON
try:
    with open('config_links.json', 'r') as f:
        data["config_urls"] = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    data["config_urls"] = {}

def save_config_links():
    """ذخیره لینک‌های کانفیگ در فایل JSON"""
    with open('config_links.json', 'w') as f:
        json.dump(data["config_urls"], f)

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

def test_links_and_send(chat_id, config_name=None):
    send_message(chat_id, "⏳ در حال دریافت و تست لینک‌ها...")
    
    if not data["config_urls"]:
        send_message(chat_id, "❌ هیچ لینک کانفیگی تنظیم نشده است.")
        return
    
    if config_name:
        url = data["config_urls"].get(config_name)
        if not url:
            send_message(chat_id, f"❌ لینک با نام '{config_name}' یافت نشد.")
            return
    else:
        # اگر نام کانفیگ مشخص نشده، از اولین لینک استفاده می‌کند
        url = next(iter(data["config_urls"].values()))

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
    if config_name:
        caption += f"\n🔗 نام کانفیگ: {config_name}"
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
            ["➕ افزودن لینک کانفیگ", "📝 ویرایش لینک کانفیگ"],
            ["🗑 حذف لینک کانفیگ", "📋 لیست لینک‌ها"],
            ["📥 دریافت کانفیگ سالم"],
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

def show_config_list(chat_id, action=None):
    if not data["config_urls"]:
        send_message(chat_id, "❌ هیچ لینک کانفیگی ذخیره نشده است.")
        return
    
    keyboard = []
    for name in data["config_urls"].keys():
        if action == "delete":
            keyboard.append([f"🗑 حذف {name}"])
        elif action == "edit":
            keyboard.append([f"📝 ویرایش {name}"])
        else:
            keyboard.append([f"🔗 {name}"])
    
    keyboard.append(["🔙 بازگشت به پنل مدیریت"])
    
    markup = {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    
    if action == "delete":
        send_message(chat_id, "لطفاً لینکی را برای حذف انتخاب کنید:", reply_markup=markup)
    elif action == "edit":
        send_message(chat_id, "لطفاً لینکی را برای ویرایش انتخاب کنید:", reply_markup=markup)
    else:
        send_message(chat_id, "لطفاً یکی از لینک‌های کانفیگ را انتخاب کنید:", reply_markup=markup)

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

            if not is_admin and data.get("join_channel_username"):
                if not check_join_channel(user_id):
                    send_message(chat_id,
                        f"❗ لطفاً ابتدا عضو کانال ما شوید: {data['join_channel_username']}\n"
                        "پس از عضویت پیام /start را ارسال کنید.")
                    continue

            if chat_id in state:
                action, *params = state[chat_id]
                if action == "add_config" and is_admin:
                    # دریافت نام کانفیگ
                    config_name = text.strip()
                    state[chat_id] = ("add_config_url", config_name)
                    send_message(chat_id, f"لطفاً لینک کانفیگ را برای نام '{config_name}' ارسال کنید:")
                    continue
                
                elif action == "add_config_url" and is_admin:
                    # دریافت لینک کانفیگ
                    config_name = params[0]
                    config_url = text.strip()
                    data["config_urls"][config_name] = config_url
                    save_config_links()
                    state.pop(chat_id)
                    send_message(chat_id, f"✅ لینک کانفیگ با نام '{config_name}' اضافه شد.")
                    admin_panel(chat_id)
                    continue
                
                elif action == "edit_config" and is_admin:
                    # دریافت نام جدید برای کانفیگ
                    old_name = params[0]
                    new_name = text.strip()
                    if new_name in data["config_urls"] and new_name != old_name:
                        send_message(chat_id, "❌ این نام قبلاً استفاده شده است. لطفاً نام دیگری انتخاب کنید.")
                        continue
                    
                    state[chat_id] = ("edit_config_url", old_name, new_name)
                    send_message(chat_id, f"لطفاً لینک جدید را برای '{new_name}' ارسال کنید:")
                    continue
                
                elif action == "edit_config_url" and is_admin:
                    # دریافت لینک جدید برای کانفیگ
                    old_name, new_name = params
                    new_url = text.strip()
                    
                    # اگر نام تغییر کرده، لینک قدیمی را حذف می‌کنیم
                    if old_name != new_name:
                        del data["config_urls"][old_name]
                    
                    data["config_urls"][new_name] = new_url
                    save_config_links()
                    state.pop(chat_id)
                    send_message(chat_id, f"✅ لینک کانفیگ با نام '{new_name}' به‌روزرسانی شد.")
                    admin_panel(chat_id)
                    continue
                
                elif action == "set_test_interval" and is_admin:
                    try:
                        interval = int(text)
                        data["auto_test_interval"] = interval
                        send_message(chat_id, f"✅ فاصله تست ذخیره شد: {interval} دقیقه")
                    except:
                        send_message(chat_id, "❌ عدد معتبر نیست.")
                    state.pop(chat_id)
                    continue
                
                elif action == "set_channel_link" and is_admin:
                    data["join_channel_username"] = text.strip()
                    data["join_channel_chat_id"] = None
                    if set_channel_chat_id():
                        send_message(chat_id, f"✅ لینک کانال ذخیره و chat_id گرفته شد: {data['join_channel_chat_id']}")
                    else:
                        send_message(chat_id, "❌ دریافت chat_id کانال موفق نبود. لطفاً آیدی را صحیح وارد کنید.")
                    state.pop(chat_id)
                    continue
                
                elif action.startswith("upload_video_") and is_admin:
                    platform = action.split("_")[-1]
                    video = message.get("video")
                    if video:
                        file_id = video["file_id"]
                        data["videos"][platform] = file_id
                        send_message(chat_id, f"✅ ویدیو {platform} ذخیره شد.")
                    else:
                        send_message(chat_id, "❌ فایل ویدیویی پیدا نشد.")
                    state.pop(chat_id)
                    continue

            # دستورات عمومی
            if text == "/start":
                if is_admin:
                    admin_panel(chat_id)
                else:
                    user_panel(chat_id)

            elif text == "➕ افزودن لینک کانفیگ" and is_admin:
                state[chat_id] = ("add_config",)
                send_message(chat_id, "لطفاً یک نام برای لینک کانفیگ جدید وارد کنید:")

            elif text == "📝 ویرایش لینک کانفیگ" and is_admin:
                show_config_list(chat_id, action="edit")

            elif text.startswith("📝 ویرایش ") and is_admin:
                config_name = text[6:]  # حذف پیشوند "📝 ویرایش "
                if config_name in data["config_urls"]:
                    state[chat_id] = ("edit_config", config_name)
                    send_message(chat_id, f"لطفاً نام جدید را برای '{config_name}' وارد کنید (یا همان نام را تکرار کنید):")
                else:
                    send_message(chat_id, "❌ لینک مورد نظر یافت نشد.")

            elif text == "🗑 حذف لینک کانفیگ" and is_admin:
                show_config_list(chat_id, action="delete")

            elif text.startswith("🗑 حذف ") and is_admin:
                config_name = text[4:]  # حذف پیشوند "🗑 حذف "
                if config_name in data["config_urls"]:
                    del data["config_urls"][config_name]
                    save_config_links()
                    send_message(chat_id, f"✅ لینک با نام '{config_name}' حذف شد.")
                    admin_panel(chat_id)
                else:
                    send_message(chat_id, "❌ لینک مورد نظر یافت نشد.")

            elif text == "📋 لیست لینک‌ها" and is_admin:
                if not data["config_urls"]:
                    send_message(chat_id, "❌ هیچ لینک کانفیگی ذخیره نشده است.")
                else:
                    message_text = "📋 لیست لینک‌های کانفیگ:\n\n"
                    for name, url in data["config_urls"].items():
                        message_text += f"🔗 {name}: {url}\n"
                    send_message(chat_id, message_text)

            elif text == "📥 دریافت کانفیگ سالم":
                if is_admin:
                    show_config_list(chat_id)
                else:
                    test_links_and_send(chat_id)

            elif text.startswith("🔗 ") and is_admin:
                config_name = text[2:]  # حذف پیشوند "🔗 "
                test_links_and_send(chat_id, config_name)

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
                platform = {
                    "📱 Android": "android",
                    "🍏 iOS": "ios",
                    "💻 Windows": "windows"
                }.get(text)
                
                if platform:
                    file_id = data["videos"].get(platform)
                    if file_id:
                        try:
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

            elif text == "⏱ تنظیم فاصله تست خودکار" and is_admin:
                state[chat_id] = ("set_test_interval",)
                send_message(chat_id, "لطفاً فاصله تست خودکار را (بر حسب دقیقه) ارسال کنید:")

            elif text == "⚙ تنظیم لینک کانال (جوین اجباری)" and is_admin:
                state[chat_id] = ("set_channel_link",)
                send_message(chat_id, "لطفاً لینک کانال را با @ وارد کنید (مثلاً @channelusername):")

            else:
                send_message(chat_id, "دستور ناشناخته یا دسترسی ندارید.")

        time.sleep(1)

if __name__ == "__main__":
    main()
