import requests
import time
import os
from datetime import datetime
import json
import base64
import socket
import re

TOKEN = "519238488:7NO7L3DzeE6BVksqnbsXLIKVkiwT5L5tePYiTOSw"
ADMIN_ID = 166912242

API_URL = f"https://tapi.bale.ai/bot{TOKEN}"
OFFSET = 0

data = {
    "config_url": "",
}

# Regex برای استخراج لینک‌ها بر اساس پروتکل‌ها
patterns = {
    "vmess": re.compile(r'(vmess://[^\s]+)'),
    "vless": re.compile(r'(vless://[^\s]+)'),
    "trojan": re.compile(r'(trojan://[^\s]+)'),
    "ss": re.compile(r'(ss://[^\s]+)'),
    "ssr": re.compile(r'(ssr://[^\s]+)'),
}

def decode_base64(data):
    """اصلاح padding و دیکد base64"""
    data = data.strip()
    missing_padding = len(data) % 4
    if missing_padding:
        data += '=' * (4 - missing_padding)
    return base64.urlsafe_b64decode(data)

def tcp_check(host, port, timeout=3):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except:
        return False

def test_vmess(link):
    # مثال vmess://base64_json
    try:
        b64 = link[len("vmess://"):]
        b64 = b64.strip()
        missing_padding = len(b64) % 4
        if missing_padding:
            b64 += '=' * (4 - missing_padding)
        decoded = base64.b64decode(b64).decode('utf-8')
        obj = json.loads(decoded)
        host = obj.get("add")
        port = int(obj.get("port", 0))
        if not host or port == 0:
            return False
        return tcp_check(host, port)
    except:
        return False

def test_vless(link):
    # vless://uuid@host:port?query
    try:
        # حذف پیشوند vless://
        content = link[len("vless://"):]
        # جدا کردن بخش اصلی و پارامترها
        if "?" in content:
            main_part = content.split("?")[0]
        else:
            main_part = content
        # format: uuid@host:port
        if "@" not in main_part:
            return False
        user_host = main_part.split("@")[1]
        if ":" not in user_host:
            return False
        host, port = user_host.split(":")
        port = int(port)
        if not host or port == 0:
            return False
        return tcp_check(host, port)
    except:
        return False

def test_trojan(link):
    # trojan://password@host:port?query
    try:
        content = link[len("trojan://"):]
        # جدا کردن بخش اصلی و پارامترها
        if "?" in content:
            main_part = content.split("?")[0]
        else:
            main_part = content
        if "@" not in main_part:
            return False
        passwd_host = main_part.split("@")[1]
        if ":" not in passwd_host:
            return False
        host, port = passwd_host.split(":")
        port = int(port)
        if not host or port == 0:
            return False
        return tcp_check(host, port)
    except:
        return False

def test_ss(link):
    # ss://base64[@host:port] یا ss://base64
    try:
        ss_content = link[len("ss://"):]
        # اگر به فرم ss://base64#name
        if "#" in ss_content:
            ss_content = ss_content.split("#")[0]

        # ممکنه ss_content به شکل base64 یا base64@host:port باشه
        # ابتدا بررسی base64 قسمت اول
        if "@" in ss_content:
            base64_part = ss_content.split("@")[0]
        else:
            base64_part = ss_content

        decoded = decode_base64(base64_part).decode('utf-8')
        # فرمت decoded معمولاً "method:password@host:port"
        if "@" not in decoded or ":" not in decoded:
            return False
        host_port = decoded.split("@")[1]
        if ":" not in host_port:
            return False
        host, port = host_port.split(":")
        port = int(port)
        if not host or port == 0:
            return False
        return tcp_check(host, port)
    except:
        return False

def test_ssr(link):
    # ssr://base64encoded
    try:
        b64 = link[len("ssr://"):]
        decoded_bytes = decode_base64(b64)
        decoded_str = decoded_bytes.decode('utf-8')
        # فرمت decoded_str : host:port:protocol:method:obfs:base64password/?params
        parts = decoded_str.split(":")
        if len(parts) < 6:
            return False
        host = parts[0]
        port = int(parts[1])
        if not host or port == 0:
            return False
        return tcp_check(host, port)
    except:
        return False

def test_link(link):
    if link.startswith("vmess://"):
        return test_vmess(link)
    elif link.startswith("vless://"):
        return test_vless(link)
    elif link.startswith("trojan://"):
        return test_trojan(link)
    elif link.startswith("ss://"):
        return test_ss(link)
    elif link.startswith("ssr://"):
        return test_ssr(link)
    else:
        return False

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{API_URL}/sendMessage", json=payload)

def send_document(chat_id, file_path):
    with open(file_path, 'rb') as f:
        requests.post(f"{API_URL}/sendDocument", files={"document": f}, data={"chat_id": chat_id})

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

def test_links_and_send(chat_id):
    send_message(chat_id, "⏳ در حال دریافت و تست لینک‌ها...")

    url = data["config_url"]
    if not url:
        send_message(chat_id, "❌ لینک فایل تنظیم نشده است.")
        return

    try:
        response = requests.get(url, timeout=10)
        content = response.text
    except Exception as e:
        send_message(chat_id, "❌ دریافت فایل با خطا مواجه شد.")
        print(f"Error downloading config: {e}")
        return

    # استخراج تمام لینک‌ها از متن بر اساس تمام پروتکل‌ها
    found_links = []
    for proto, pattern in patterns.items():
        found_links.extend(pattern.findall(content))

    if not found_links:
        send_message(chat_id, "❌ لینک پراکسی در فایل پیدا نشد.")
        return

    valid_links = []
    total = len(found_links)
    checked = 0

    for link in found_links:
        if test_link(link):
            valid_links.append(link)
        checked += 1
        if checked % 20 == 0:
            send_message(chat_id, f"✅ بررسی {checked} از {total} لینک...")

    if not valid_links:
        send_message(chat_id, "❌ هیچ لینک سالمی پیدا نشد.")
        return

    filename = f"valid_config_{chat_id}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(valid_links))
        f.write(f"\n\n📅 بررسی شده در {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    send_document(chat_id, filename)
    os.remove(filename)
    send_message(chat_id, f"✅ تعداد {len(valid_links)} لینک سالم ارسال شد.")

def show_admin_panel(chat_id):
    markup = {
        "keyboard": [
            ["🔗 تنظیم لینک فایل", "📥 دریافت لینک‌های سالم"]
        ],
        "resize_keyboard": True
    }
    send_message(chat_id, "🎛 پنل ادمین", reply_markup=markup)

def main():
    global OFFSET
    print("ربات در حال اجراست ...")
    waiting = {}

    while True:
        updates = get_updates()
        for update in updates:
            OFFSET = update["update_id"]
            msg = update.get("message")
            if not msg:
                continue

            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")

            if chat_id in waiting:
                state = waiting.pop(chat_id)
                if state == "set_config":
                    data["config_url"] = text.strip()
                    send_message(chat_id, "✅ لینک ذخیره شد.")
                continue

            if text == "/start":
                if msg["from"]["id"] == ADMIN_ID:
                    show_admin_panel(chat_id)
                else:
                    send_message(chat_id, "این ربات فقط مخصوص مدیر است.")

            elif text == "🔗 تنظیم لینک فایل":
                waiting[chat_id] = "set_config"
                send_message(chat_id, "لینک فایل .txt را وارد کنید:")

            elif text == "📥 دریافت لینک‌های سالم":
                if chat_id == ADMIN_ID:
                    test_links_and_send(chat_id)
                else:
                    send_message(chat_id, "❌ شما اجازه دسترسی به این قسمت را ندارید.")

        time.sleep(1)

if __name__ == "__main__":
    main()

