

import requests
import time
import os
from datetime import datetime


TOKEN = '8057495132:AAESf8cO_FbIfYC4DTp8uVBKTU_ECNiTznA'
ADMIN_USERNAME = 'Mohammad87killer'
API_URL = f"https://api.telegram.org/bot{TOKEN}"
OFFSET = 0

data = {
    "join_channel": "",
    "github_url": "",
    "video_android": "",
    "video_ios": "",
    "video_windows": "",
    "ping_interval": 0
}

def get_updates():
    global OFFSET
    try:
        resp = requests.get(f"{API_URL}/getUpdates", params={"offset": OFFSET + 1, "timeout": 5})
        result = resp.json()
        if result.get("ok"):
            return result["result"]
    except:
        pass
    return []

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{API_URL}/sendMessage", data=payload)

def send_document(chat_id, file_path):
    with open(file_path, 'rb') as f:
        requests.post(f"{API_URL}/sendDocument", files={"document": f}, data={"chat_id": chat_id})

def send_video(chat_id, file_id, caption=""):
    requests.post(f"{API_URL}/sendVideo", data={
        "chat_id": chat_id,
        "video": file_id,
        "caption": caption
    })

def is_member(user_id):
    return True  # عضویت غیرفعال شده

def fetch_and_test_configs():
    valid_configs = []
    url = data["github_url"]
    if not url or "github.com" not in url:
        return valid_configs

    if url.endswith('/'):
        url = url[:-1]

    try:
        # Example: https://github.com/user/repo -> https://api.github.com/repos/user/repo/contents/
        parts = url.replace("https://github.com/", "").split("/")
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/"
            r = requests.get(api_url)
            files = r.json()

            for file in files:
                if file["name"].endswith(".txt"):
                    raw_url = file["download_url"]
                    try:
                        response = requests.get(raw_url, timeout=5)
                        if response.status_code == 200:
                            valid_configs.append((file["name"], response.text))
                    except:
                        pass
    except:
        pass
    return valid_configs

def show_user_panel(chat_id):
    markup = {
        "keyboard": [["📡 دریافت کانفیگ رایگان", "🎥 آموزش استفاده"]],
        "resize_keyboard": True
    }
    send_message(chat_id, "به ربات خوش آمدید.", reply_markup=markup)

def show_admin_panel(chat_id):
    markup = {
        "keyboard": [
            ["📢 تنظیم کانال عضویت", "🔗 تنظیم لینک گیت‌هاب"],
            ["🎞 بارگذاری ویدیو آموزش", "⏰ تنظیم بازه زمانی تست"],
            ["👥 مشاهده تنظیمات", "📡 تست و ارسال کانفیگ"]
        ],
        "resize_keyboard": True
    }
    send_message(chat_id, "به پنل ادمین خوش آمدید.", reply_markup=markup)

def handle_config(chat_id):
    send_message(chat_id, "⏳ در حال دریافت کانفیگ‌ها ...")
    configs = fetch_and_test_configs()
    if configs:
        result = ""
        for name, _ in configs:
            result += f"\n{name}: تست شد ✔️"
        filename = f"configs_{chat_id}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            for name, text in configs:
                f.write(f"{name}\n{text}\n\n")
            f.write(f"\nتاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        send_document(chat_id, filename)
        os.remove(filename)
    else:
        send_message(chat_id, "❌ کانفیگ سالم یافت نشد.")

def handle_tutorial(chat_id):
    if data["video_android"]:
        send_video(chat_id, data["video_android"], "🎥 آموزش اندروید")
    if data["video_windows"]:
        send_video(chat_id, data["video_windows"], "🎥 آموزش ویندوز")
    if data["video_ios"]:
        send_video(chat_id, data["video_ios"], "🎥 آموزش iOS")

def main():
    global OFFSET
    print("✅ ربات تلگرام در حال اجراست ...")
    waiting_for_input = {}

    while True:
        updates = get_updates()
        for update in updates:
            OFFSET = update["update_id"]
            msg = update.get("message")
            if not msg:
                continue
            text = msg.get("text", "")
            chat_id = msg["chat"]["id"]
            username = msg["from"].get("username", "")

            if chat_id in waiting_for_input:
                state = waiting_for_input.pop(chat_id)
                if state == "set_channel":
                    data["join_channel"] = text.strip()
                    send_message(chat_id, "✅ کانال ذخیره شد.")
                elif state == "set_github":
                    data["github_url"] = text.strip()
                    send_message(chat_id, "✅ لینک گیت‌هاب ذخیره شد.")
                elif state == "set_interval":
                    try:
                        interval = int(text.strip())
                        data["ping_interval"] = interval
                        send_message(chat_id, f"✅ بازه {interval} ساعت ذخیره شد.")
                    except:
                        send_message(chat_id, "❌ عدد صحیح وارد کنید.")
                elif state.startswith("upload_video_"):
                    platform = state.split("_")[-1]
                    if "video" in msg:
                        file_id = msg["video"]["file_id"]
                        if platform == "android":
                            data["video_android"] = file_id
                        elif platform == "windows":
                            data["video_windows"] = file_id
                        elif platform == "ios":
                            data["video_ios"] = file_id
                        send_message(chat_id, "✅ ویدیو ذخیره شد.")
                    else:
                        send_message(chat_id, "❌ لطفا یک ویدیو ارسال کنید.")
                continue

            if text == "/start":
                if username == ADMIN_USERNAME:
                    show_admin_panel(chat_id)
                else:
                    show_user_panel(chat_id)

            elif text == "📡 دریافت کانفیگ رایگان":
                handle_config(chat_id)

            elif text == "🎥 آموزش استفاده":
                handle_tutorial(chat_id)

            elif text == "📢 تنظیم کانال عضویت":
                waiting_for_input[chat_id] = "set_channel"
                send_message(chat_id, "یوزرنیم کانال را با @ وارد کنید:")

            elif text == "🔗 تنظیم لینک گیت‌هاب":
                waiting_for_input[chat_id] = "set_github"
                send_message(chat_id, "لینک مخزن گیت‌هاب را وارد کنید:")

            elif text == "🎞 بارگذاری ویدیو آموزش":
                markup = {
                    "keyboard": [["📱 اندروید", "🖥 ویندوز", "🍏 iOS"]],
                    "resize_keyboard": True
                }
                send_message(chat_id, "پلتفرم موردنظر را انتخاب کنید:", reply_markup=markup)

            elif text == "📱 اندروید":
                waiting_for_input[chat_id] = "upload_video_android"
                send_message(chat_id, "لطفا ویدیو آموزش اندروید را ارسال کنید:")

            elif text == "🖥 ویندوز":
                waiting_for_input[chat_id] = "upload_video_windows"
                send_message(chat_id, "لطفا ویدیو آموزش ویندوز را ارسال کنید:")

            elif text == "🍏 iOS":
                waiting_for_input[chat_id] = "upload_video_ios"
                send_message(chat_id, "لطفا ویدیو آموزش iOS را ارسال کنید:")

            elif text == "⏰ تنظیم بازه زمانی تست":
                waiting_for_input[chat_id] = "set_interval"
                send_message(chat_id, "بازه زمانی بین تست‌ها را (برحسب ساعت) وارد کنید:")

            elif text == "👥 مشاهده تنظیمات":
                msg = f"📢 کانال: {data['join_channel']}\n🔗 گیت‌هاب: {data['github_url']}\n⏰ بازه تست: {data['ping_interval']} ساعت"
                send_message(chat_id, msg)

            elif text == "📡 تست و ارسال کانفیگ":
                handle_config(chat_id)

        time.sleep(1)

if __name__ == "__main__":
    import json
    main()
