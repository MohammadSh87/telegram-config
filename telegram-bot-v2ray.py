import requests
import os
from datetime import datetime

TOKEN = "8057495132:AAESf8cO_FbIfYC4DTp8uVBKTU_ECNiTznA"
ADMIN_ID = 2075973663  # شناسه ادمین را اینجا بگذارید
URL = f"https://api.telegram.org/bot{TOKEN}/"

data = {
    "config_urls": [],
    "auto_test_interval": 0,
    "channel_username": "",
    "force_join": False,
    # بقیه تنظیمات شما اینجا می‌ماند بدون تغییر
}

state = {}

def get_updates(offset=None):
    params = {"timeout": 100, "offset": offset}
    response = requests.get(URL + "getUpdates", params=params)
    if response.status_code == 200:
        return response.json().get("result", [])
    return []

def send_message(chat_id, text, reply_markup=None):
    params = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        params["reply_markup"] = reply_markup
    requests.post(URL + "sendMessage", json=params)

def send_document(chat_id, filepath, caption=None):
    with open(filepath, "rb") as f:
        files = {"document": f}
        data_ = {"chat_id": chat_id}
        if caption:
            data_["caption"] = caption
            data_["parse_mode"] = "Markdown"
        requests.post(URL + "sendDocument", data=data_, files=files)

def is_user_admin(user_id):
    return user_id == ADMIN_ID

def send_config_links_buttons(chat_id):
    if not data["config_urls"]:
        send_message(chat_id, "هیچ لینکی ذخیره نشده است.")
        return
    keyboard = [[f"لینک {i+1}"] for i in range(len(data["config_urls"]))]
    reply_markup = {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    send_message(chat_id, "لطفاً لینک مورد نظر را انتخاب کنید:", reply_markup=reply_markup)

def test_links_and_send(chat_id, url):
    send_message(chat_id, f"⏳ در حال دریافت و تست لینک‌ها از:\n{url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
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
            continue

    if not valid_links:
        send_message(chat_id, "❌ هیچ لینکی سالم نبود.")
        return

    filename = f"valid_config_{chat_id}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(valid_links))

    caption = f"🕒 تست شده در: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n⏱ فاصله تست خودکار: {data['auto_test_interval']} دقیقه"
    send_document(chat_id, filename, caption=caption)
    os.remove(filename)

def main():
    OFFSET = None
    while True:
        updates = get_updates(OFFSET)
        for update in updates:
            OFFSET = update["update_id"] + 1
            message = update.get("message")
            if not message:
                continue
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            user_id = message["from"]["id"]
            is_admin = is_user_admin(user_id)

            # وضعیت اضافه کردن لینک
            if chat_id in state:
                action = state.pop(chat_id)
                if action == "add_config_url" and is_admin:
                    url = text.strip()
                    if url.startswith("http"):
                        data["config_urls"].append(url)
                        send_message(chat_id, "✅ لینک اضافه شد.")
                    else:
                        send_message(chat_id, "❌ لینک نامعتبر است.")
                    continue
                elif action == "remove_config_url" and is_admin:
                    try:
                        idx = int(text.strip()) - 1
                        if 0 <= idx < len(data["config_urls"]):
                            removed = data["config_urls"].pop(idx)
                            send_message(chat_id, f"✅ لینک حذف شد:\n{removed}")
                        else:
                            send_message(chat_id, "❌ شماره نامعتبر است.")
                    except:
                        send_message(chat_id, "❌ لطفاً شماره لینک را به صورت عدد وارد کنید.")
                    continue

            # دستورات پنل ادمین
            if is_admin:
                if text == "➕ افزودن لینک کانفیگ":
                    state[chat_id] = "add_config_url"
                    send_message(chat_id, "لطفاً لینک کانفیگ را ارسال کنید:")
                    continue
                elif text == "🗑️ حذف لینک کانفیگ":
                    if not data["config_urls"]:
                        send_message(chat_id, "لیست لینک‌ها خالی است.")
                    else:
                        text_links = "\n".join([f"{i+1}. {url}" for i, url in enumerate(data["config_urls"])])
                        send_message(chat_id, f"شماره لینک مورد نظر برای حذف را ارسال کنید:\n{text_links}")
                        state[chat_id] = "remove_config_url"
                    continue
                elif text == "🔗 نمایش لینک‌ها":
                    if not data["config_urls"]:
                        send_message(chat_id, "هیچ لینکی ذخیره نشده است.")
                    else:
                        text_links = "\n".join([f"{i+1}. {url}" for i, url in enumerate(data["config_urls"])])
                        send_message(chat_id, f"لینک‌های ذخیره شده:\n{text_links}")
                    continue
                elif text == "📥 دریافت کانفیگ سالم":
                    send_config_links_buttons(chat_id)
                    continue

                # بقیه دستورات ادمین (مثلاً تنظیمات فاصله تست و کانال) اینجا بدون تغییر می‌آیند
                # مثلا:
                if text.startswith("⏱ تنظیم فاصله تست خودکار "):
                    try:
                        minutes = int(text.split()[-1])
                        data["auto_test_interval"] = minutes
                        send_message(chat_id, f"✅ فاصله تست خودکار روی {minutes} دقیقه تنظیم شد.")
                    except:
                        send_message(chat_id, "❌ مقدار معتبر وارد کنید.")
                    continue
                if text.startswith("🔔 تنظیم کانال "):
                    channel = text.split()[-1]
                    data["channel_username"] = channel
                    send_message(chat_id, f"✅ کانال به {channel} تنظیم شد.")
                    continue
                if text == "🔒 فعال/غیرفعال اجباری جوین":
                    data["force_join"] = not data["force_join"]
                    send_message(chat_id, f"✅ حالت اجباری جوین {'فعال' if data['force_join'] else 'غیرفعال'} شد.")
                    continue

            # کاربر عادی یا ادمین که لینک را انتخاب کرده
            if text.startswith("لینک "):
                try:
                    idx = int(text.split()[1]) - 1
                    if 0 <= idx < len(data["config_urls"]):
                        test_links_and_send(chat_id, data["config_urls"][idx])
                    else:
                        send_message(chat_id, "❌ لینک نامعتبر است.")
                except:
                    send_message(chat_id, "❌ فرمت لینک انتخابی نامعتبر است.")
                continue

            # دستورات عمومی دیگر (مانند استارت، دستور جوین، تست، و غیره) بدون تغییر اینجا قرار بگیرند
            if text == "/start":
                send_message(chat_id, "سلام! برای دریافت کانفیگ سالم، از منوی دریافت استفاده کنید.")
                continue

            # پیام پیش‌فرض برای دستور نامشخص
            send_message(chat_id, "دستور نامشخص است. لطفاً از منوی موجود استفاده کنید.")

if __name__ == "__main__":
    main()
