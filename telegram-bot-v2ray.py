import json
import requests
import threading
import time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

TOKEN = "8057495132:AAESf8cO_FbIfYC4DTp8uVBKTU_ECNiTznA"
ADMIN_ID = 2075973663

data_file = 'data.json'
state = {}

# ---------- Utility ----------
def load_data():
    try:
        with open(data_file, 'r') as f:
            return json.load(f)
    except:
        return {"config_urls": []}

def save_data(data):
    with open(data_file, 'w') as f:
        json.dump(data, f)

def send_main_menu(chat_id, context):
    keyboard = [
        [KeyboardButton("📥 دریافت کانفیگ سالم")],
        [KeyboardButton("➕ افزودن لینک کانفیگ"), KeyboardButton("🗑️ حذف لینک کانفیگ")],
        [KeyboardButton("🔗 نمایش لینک‌ها")]
    ]
    context.bot.send_message(chat_id, "پنل مدیریت:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

def is_admin(update: Update):
    return update.effective_user.username == ADMIN_USERNAME

# ---------- Bot Logic ----------
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    update.message.reply_text(f"سلام {user.first_name}!")
    if is_admin(update):
        send_main_menu(update.message.chat_id, context)

def handle_text(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    text = update.message.text.strip()
    data = load_data()

    if chat_id in state:
        current_state = state[chat_id]
        if current_state == "add":
            data["config_urls"].append(text)
            save_data(data)
            update.message.reply_text("✅ لینک ذخیره شد.")
            del state[chat_id]
            return
        elif current_state == "remove":
            try:
                index = int(text) - 1
                removed = data["config_urls"].pop(index)
                save_data(data)
                update.message.reply_text(f"✅ لینک حذف شد:\n{removed}")
            except:
                update.message.reply_text("شماره نامعتبر است.")
            del state[chat_id]
            return

    # دستورات مدیریتی
    if text == "➕ افزودن لینک کانفیگ" and is_admin(update):
        state[chat_id] = "add"
        update.message.reply_text("لینک را ارسال کنید:")
    elif text == "🗑️ حذف لینک کانفیگ" and is_admin(update):
        if not data["config_urls"]:
            update.message.reply_text("⛔️ لیست خالی است.")
        else:
            msg = "\n".join([f"{i+1}. {url}" for i, url in enumerate(data["config_urls"])])
            update.message.reply_text(f"لینک‌ها:\n{msg}\nشماره لینک برای حذف را بفرست:")
            state[chat_id] = "remove"
    elif text == "🔗 نمایش لینک‌ها" and is_admin(update):
        if not data["config_urls"]:
            update.message.reply_text("⛔️ هیچ لینکی ذخیره نشده.")
        else:
            msg = "\n".join([f"{i+1}. {url}" for i, url in enumerate(data["config_urls"])])
            update.message.reply_text(f"📄 لینک‌ها:\n{msg}")
    elif text == "📥 دریافت کانفیگ سالم":
        if not data["config_urls"]:
            update.message.reply_text("⛔️ هیچ لینکی ذخیره نشده.")
        else:
            buttons = [
                [InlineKeyboardButton(f"لینک {i+1}", callback_data=f"check_{i}")]
                for i in range(len(data["config_urls"]))
            ]
            context.bot.send_message(chat_id, "🌐 یکی از لینک‌ها را انتخاب کن:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        update.message.reply_text("دستور نامعتبر است.")

def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat_id
    query.answer()

    if query.data.startswith("check_"):
        index = int(query.data.split("_")[1])
        data = load_data()
        if index >= len(data["config_urls"]):
            query.edit_message_text("❌ لینک وجود ندارد.")
            return
        url = data["config_urls"][index]
        query.edit_message_text("⏳ در حال دریافت و تست کانفیگ‌ها...")

        try:
            response = requests.get(url, timeout=10)
            raw = response.text.strip()
            configs = [line for line in raw.splitlines() if line.startswith("vmess://") or line.startswith("vless://") or line.startswith("trojan://")]

            healthy = []
            for conf in configs:
                if test_config(conf):
                    healthy.append(conf)

            if not healthy:
                context.bot.send_message(chat_id, "⛔️ هیچ کانفیگ سالمی پیدا نشد.")
            else:
                msg = "\n".join(healthy)
                context.bot.send_message(chat_id, f"✅ کانفیگ‌های سالم ({len(healthy)}):\n\n{msg}")
        except:
            context.bot.send_message(chat_id, "❌ خطا در دریافت کانفیگ‌ها.")

# ---------- Ping Test ----------
import subprocess
import base64
from urllib.parse import urlparse

def test_config(link):
    try:
        if link.startswith("vmess://"):
            raw = link[8:]
            decoded = base64.b64decode(raw + '=' * (-len(raw) % 4)).decode('utf-8')
            server = json.loads(decoded).get("add")
        else:
            server = urlparse(link).hostname

        if not server:
            return False

        result = subprocess.run(["ping", "-c", "1", "-W", "1", server], stdout=subprocess.DEVNULL)
        return result.returncode == 0
    except:
        return False

# ---------- Run ----------
updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
dp.add_handler(CallbackQueryHandler(handle_callback))

print("ربات اجرا شد.")
updater.start_polling()
updater.idle()
