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

CONFIG_FILE = 'config_links.json'

def load_config():
    """بارگذاری داده‌ها از فایل JSON"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                if isinstance(loaded_data, dict):
                    data["config_urls"] = loaded_data
                else:
                    print("Error: Config file format is invalid")
                    data["config_urls"] = {}
        else:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error loading config file: {e}")
        data["config_urls"] = {}

def save_config():
    """ذخیره لینک‌های کانفیگ در فایل JSON"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data["config_urls"], f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config file: {e}")
        return False

# بارگذاری اولیه داده‌ها
load_config()

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
        configs_to_test = {config_name: url}
    else:
        configs_to_test = data["config_urls"]

    valid_configs = {}
    
    for name, url in configs_to_test.items():
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                valid_configs[name] = []
                continue
                
            content = response.text
            lines = content.strip().splitlines()
            valid_links = []
            
            for link in lines:
                link = link.strip()
                if not link:
                    continue
                
                if link.startswith("http"):
                    try:
                        r = requests.head(link, timeout=3)
                        if r.status_code == 200:
                            valid_links.append(link)
                    except:
                        continue
                elif any(link.startswith(proto) for proto in ["vmess://", "vless://", "ss://", "trojan://", "ssr://"]):
                    valid_links.append(link)
            
            valid_configs[name] = valid_links
            
        except Exception as e:
            print(f"Error testing config {name}:", e)
            valid_configs[name] = []
            continue

    if config_name:
        if not valid_configs[config_name]:
            send_message(chat_id, f"❌ هیچ لینک سالمی در کانفیگ '{config_name}' یافت نشد.")
            return
            
        filename = f"valid_config_{chat_id}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(valid_configs[config_name]))

        caption = f"🕒 تست شده در: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n⏱ فاصله تست خودکار: {data['auto_test_interval']} دقیقه\n🔗 نام کانفیگ: {config_name}"
        send_document(chat_id, filename, caption=caption)
        os.remove(filename)
    else:
        has_valid = False
        for name, links in valid_configs.items():
            if links:
                has_valid = True
                filename = f"valid_config_{name}_{chat_id}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("\n".join(links))

                caption = f"🕒 تست شده در: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n⏱ فاصله تست خودکار: {data['auto_test_interval']} دقیقه\n🔗 نام کانفیگ: {name}"
                send_document(chat_id, filename, caption=caption)
                os.remove(filename)
                time.sleep(1)
        
        if not has_valid:
            send_message(chat_id, "❌ هیچ لینک سالمی در هیچ یک از کانفیگ‌ها یافت نشد.")

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
            keyboard.append([f"✏️ ویرایش {name}"])
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

def handle_config_edit(chat_id, config_name):
    if config_name not in data["config_urls"]:
        send_message(chat_id, f"❌ لینک با نام '{config_name}' یافت نشد.")
        return
    
    state[chat_id] = ("edit_config", config_name)
    send_message(chat_id, f"لطفاً نام جدید را برای کانفیگ '{config_name}' وارد کنید (یا برای حفظ نام فعلی، همان نام را تکرار کنید):\n\nلینک فعلی: {data['config_urls'][config_name]}")

def handle_config_delete(chat_id, config_name):
    if config_name not in data["config_urls"]:
        send_message(chat_id, f"❌ لینک با نام '{config_name}' یافت نشد.")
        return
    
    markup = {
        "keyboard": [
            ["✅ بله، حذف کن"],
            ["❌ خیر، لغو کن"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    state[chat_id] = ("confirm_delete", config_name)
    send_message(chat_id, f"آیا مطمئن هستید که می‌خواهید لینک '{config_name}' را حذف کنید؟\n\nلینک: {data['config_urls'][config_name]}", reply_markup=markup)

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
                    config_name = text.strip()
                    if not config_name:
                        send_message(chat_id, "❌ نام کانفیگ نمی‌تواند خالی باشد.")
                        continue
                    if config_name in data["config_urls"]:
                        send_message(chat_id, "⚠️ این نام قبلاً استفاده شده است. لطفاً نام دیگری انتخاب کنید.")
                        continue
                    state[chat_id] = ("add_config_url", config_name)
                    send_message(chat_id, f"لطفاً لینک کانفیگ را برای نام '{config_name}' ارسال کنید:")
                    continue
                
                elif action == "add_config_url" and is_admin:
                    config_name = params[0]
                    config_url = text.strip()
                    if not config_url.startswith(('http://', 'https://')):
                        send_message(chat_id, "❌ لینک باید با http:// یا https:// شروع شود.")
                        continue
                    
                    data["config_urls"][config_name] = config_url
                    if save_config():
                        send_message(chat_id, f"✅ لینک کانفیگ با نام '{config_name}' با موفقیت ذخیره شد.")
                    else:
                        send_message(chat_id, f"⚠️ لینک ذخیره شد اما ذخیره در فایل با مشکل مواجه شد!")
                    state.pop(chat_id)
                    admin_panel(chat_id)
                    continue
                
                elif action == "edit_config" and is_admin:
                    old_name = params[0]
                    new_name = text.strip()
                    if not new_name:
                        send_message(chat_id, "❌ نام کانفیگ نمی‌تواند خالی باشد.")
                        continue
                    if new_name in data["config_urls"] and new_name != old_name:
                        send_message(chat_id, "❌ این نام قبلاً استفاده شده است. لطفاً نام دیگری انتخاب کنید.")
                        continue
                    
                    state[chat_id] = ("edit_config_url", old_name, new_name)
                    send_message(chat_id, f"لطفاً لینک جدید را برای '{new_name}' ارسال کنید:\n\nلینک فعلی: {data['config_urls'][old_name]}")
                    continue
                
                elif action == "edit_config_url" and is_admin:
                    old_name, new_name = params
                    new_url = text.strip()
                    
                    if not new_url.startswith(('http://', 'https://')):
                        send_message(chat_id, "❌ لینک باید با http:// یا https:// شروع شود.")
                        continue
                    
                    if old_name != new_name:
                        del data["config_urls"][old_name]
                    
                    data["config_urls"][new_name] = new_url
                    if save_config():
                        send_message(chat_id, f"✅ لینک کانفیگ با نام '{new_name}' با موفقیت به‌روزرسانی شد.")
                    else:
                        send_message(chat_id, f"⚠️ لینک به‌روزرسانی شد اما ذخیره در فایل با مشکل مواجه شد!")
                    state.pop(chat_id)
                    admin_panel(chat_id)
                    continue
                
                elif action == "confirm_delete" and is_admin:
                    config_name = params[0]
                    if text == "✅ بله، حذف کن":
                        if config_name in data["config_urls"]:
                            del data["config_urls"][config_name]
                            if save_config():
                                send_message(chat_id, f"✅ لینک با نام '{config_name}' با موفقیت حذف شد.")
                            else:
                                send_message(chat_id, f"⚠️ لینک حذف شد اما ذخیره فایل با مشکل مواجه شد!")
                        else:
                            send_message(chat_id, f"❌ لینک با نام '{config_name}' یافت نشد.")
                    elif text == "❌ خیر، لغو کن":
                        send_message(chat_id, "❌ عمل حذف لغو شد.")
                    else:
                        send_message(chat_id, "دستور نامعتبر!")
                    
                    state.pop(chat_id)
                    admin_panel(chat_id)
                    continue

            # دستورات عمومی
            if text == "/start":
                if is_admin:
                    admin_panel(chat_id)
                else:
                    user_panel(chat_id)

            elif text == "➕ افزودن لینک کانفیگ" and is_admin:
                state[chat_id] = ("add_config",)
                send_message(chat_id, "لطفاً یک نام منحصر به فرد برای لینک کانفیگ جدید وارد کنید:")

            elif text == "📝 ویرایش لینک کانفیگ" and is_admin:
                show_config_list(chat_id, action="edit")

            elif text == "🗑 حذف لینک کانفیگ" and is_admin:
                show_config_list(chat_id, action="delete")

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

            elif text.startswith("🗑 حذف ") and is_admin:
                config_name = text[4:].strip()
                handle_config_delete(chat_id, config_name)

            elif text.startswith("✏️ ویرایش ") and is_admin:
                config_name = text[5:].strip()
                handle_config_edit(chat_id, config_name)

            elif text.startswith("🔗 ") and is_admin:
                config_name = text[2:].strip()
                test_links_and_send(chat_id, config_name)

            elif text == "🔙 بازگشت به پنل مدیریت":
                admin_panel(chat_id)

            else:
                if is_admin:
                    send_message(chat_id, "دستور ناشناخته! لطفاً از منوی مدیریت استفاده کنید.")
                else:
                    send_message(chat_id, "دستور ناشناخته! لطفاً از منوی کاربری استفاده کنید.")

        time.sleep(1)

if __name__ == "__main__":
    main()
