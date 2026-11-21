
import os
import logging
import sqlite3
import asyncio
import requests

from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# SOZLAMALAR
# =========================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-3.5-flash-lite"

PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_URL = (
    os.getenv("RENDER_EXTERNAL_URL")
    or os.getenv("WEBHOOK_URL")
)

DB = "zentro_memory.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# =========================
# DATABASE
# =========================

def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT
            )
        """)


def get_history(user_id):
    with sqlite3.connect(DB) as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 12
            """,
            (user_id,),
        ).fetchall()

    return [
        {"role": role, "parts": [{"text": content}]}
        for role, content in reversed(rows)
    ]


def save_message(user_id, role, content):
    with sqlite3.connect(DB) as conn:
        conn.execute(
            """
            INSERT INTO messages (user_id, role, content)
            VALUES (?, ?, ?)
            """,
            (user_id, role, content),
        )


def clear_history(user_id):
    with sqlite3.connect(DB) as conn:
        conn.execute(
            "DELETE FROM messages WHERE user_id = ?",
            (user_id,),
        )


# =========================
# GEMINI AI
# =========================

def ask_gemini(history, message):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{MODEL}:generateContent"
    )

    contents = history + [
        {"role": "user", "parts": [{"text": message}]}
    ]

    data = {
        "system_instruction": {
            "parts": [{
                "text": (
                    "Sen ZENTRO AI nomli aqlli yordamchisan. "
                    "Tabiiy, samimiy, hazilkash va hurmatli "
                    "o'zbek tilida gaplash. O'tkir va qiziqarli "
                    "javob ber, lekin haqorat qilma. "
                    "Savollarga aniq va foydali javob ber."
                )
            }]
        },
        "contents": contents,
    }

    response = requests.post(
        url,
        params={"key": GEMINI_API_KEY},
        json=data,
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            f"Gemini API xatosi: HTTP {response.status_code}"
        )

    result = response.json()

    candidates = result.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini javob qaytarmadi.")

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise RuntimeError("Gemini javobi bo'sh.")

    return parts[0].get("text", "Javob topilmadi.")


# =========================
# TELEGRAM MENYU
# =========================

keyboard = ReplyKeyboardMarkup(
    [
        ["💬 AI bilan suhbat"],
        ["🧠 Xotirani tozalash"],
        ["ℹ️ Bot haqida"],
        ["👨‍💻 Seni kim yaratgan?"],
    ],
    resize_keyboard=True,

)


# =========================
# BUYRUQLAR
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Assalomu alaykum!\n\n"
        "Men ZENTRO AI — aqlli yordamchingizman.\n"
        "Savollaringizga javob beraman va suhbat tarixini saqlayman.\n\n"
        "Boshlash uchun xabar yozing!",
        reply_markup=keyboard,
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_history(update.effective_user.id)
    await update.message.reply_text(
        "🧠 Suhbat xotirasi tozalandi!"
    )


# =========================
# AI SUHBAT
# =========================

n




    
    if message == "ℹ️ Bot haqida":
        await update.message.reply_text(
            "ZENTRO AI 🤖\n"
            "Gemini asosidagi aqlli yordamchi."
        )
        return
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text

    if message == "🧠 Xotirani tozalash":
        await clear(update, context)
        return

    
    if message == "👨‍💻 Seni kim yaratgan?":
        await update.message.reply_text(
            "🤖 Men ZENTRO AI botiman!\n\n"
            "👨‍💻 Meni @uz207z yaratgan! 🚀\n\n"
            "Sizga yordam berish uchun shu yerdaman!"
             retur
        )
        
            

    if message == "💬 AI bilan suhbat":
        await update.message.reply_text(
            "Marhamat! Savolingizni yozing."
        )
        return

    await update.message.chat.send_action("typing")

    try:
        history = get_history(user_id)

        answer = await asyncio.to_thread(
            ask_gemini,
            history,
            message,
        )

        save_message(user_id, "user", message)
        save_message(user_id, "model", answer)

        for i in range(0, len(answer), 4000):
            await update.message.reply_text(answer[i:i + 4000])

    except Exception:
        logger.exception("AI bilan suhbatda xato")
        await update.message.reply_text(
            "Kechirasiz, hozir texnik muammo yuz berdi."
        )


# =========================
# BOTNI ISHGA TUSHIRISH
# =========================

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN topilmadi!")

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY topilmadi!")

    if not WEBHOOK_URL:
        raise ValueError("Render server manzili topilmadi!")

    init_db()

    # Webhook faqat run_webhook orqali o'rnatiladi.
    # post_init orqali ikkinchi marta set_webhook chaqirilmaydi.
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            chat,
        )
    )

    print("ZENTRO AI SERVERDA ISHGA TUSHDI!")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL.rstrip('/')}/{BOT_TOKEN}",
        secret_token=None,
    )


if __name__ == "__main__":
    main()
