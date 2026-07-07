from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import os, json

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("Set BOT_TOKEN")

PORT = int(os.environ.get("PORT", 10000))
DATA_FILE = "/tmp/kaspi_chat.json"

chats = {}

def load_chats():
    global chats
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            chats = json.load(f)
            chats = {int(k): {"users": v["users"], "balance": float(v["balance"])} for k, v in chats.items()}
    except FileNotFoundError:
        chats = {}

def save_chats():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(chats, f, ensure_ascii=False, indent=2)

def get_chat(chat_id: int):
    if chat_id not in chats:
        chats[chat_id] = {"users": [], "balance": 0.0}
    return chats[chat_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update.effective_chat.id)
    user_id = update.effective_user.id
    if user_id not in chat["users"]:
        if len(chat["users"]) < 2:
            chat["users"].append(user_id)
            role = "плюсует (+)" if len(chat["users"]) == 1 else "минусует (-)"
        else:
            await update.message.reply_text("В этом чате уже есть два участника. Сначала сбросьте счёт /reset")
            return
    else:
        role = "плюсует (+)" if chat["users"][0] == user_id else "минусует (-)"
    await update.message.reply_text(
        f"Счёт запущен.\n"
        f"Вы — участник №{chat['users'].index(user_id)+1} ({role}).\n"
        f"Просто отправьте число."
    )
    save_chats()

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update.effective_chat.id)
    chat["users"] = []
    chat["balance"] = 0.0
    save_chats()
    await update.message.reply_text("Счёт сброшен. Нажмите /start, чтобы зарегистрировать первого участника.")

async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update.effective_chat.id)
    user_id = update.effective_user.id
    if len(chat["users"]) != 2:
        await update.message.reply_text("Сначала оба пользователя должны нажать /start.")
        return
    try:
        value = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Нужно число.")
        return
    if user_id == chat["users"][0]:
        delta = value
    elif user_id == chat["users"][1]:
        delta = -value
    else:
        await update.message.reply_text("Вы не участник этого счёта.")
        return
    chat["balance"] += delta
    save_chats()
    await update.message.reply_text(f"Итого: {chat['balance']:.2f}")

def main():
    load_chats()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))
    print("Bot polling started")
    app.run_polling()

if __name__ == "__main__":
    main()
