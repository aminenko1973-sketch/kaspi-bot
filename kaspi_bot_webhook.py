from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8941197384:***")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "kaspi_secret_2026")
PORT = int(os.environ.get("PORT", 10000))
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://kaspi-bot-musm.onrender.com").rstrip("/")

chats: dict = {}

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

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = get_chat(update.effective_chat.id)
    chat["users"] = []
    chat["balance"] = 0.0
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
    await update.message.reply_text(f"Итого: {chat['balance']:.2f}")

app = FastAPI()
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("reset", reset))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))

@app.on_event("startup")
async def startup():
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.bot.set_webhook(url=f"{RENDER_URL}/webhook/{WEBHOOK_SECRET}", allowed_updates=Update.ALL_TYPES)

@app.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        return JSONResponse({"ok": False}, status_code=403)
    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return JSONResponse({"ok": True})

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
