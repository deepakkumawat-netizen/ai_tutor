#!/usr/bin/env python3
"""
CodeVidhya AI Tutor — Telegram Bot
Full AI Tutor experience inside Telegram
"""

import os
import asyncio
import threading
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from mcp_server import get_topics, explain_topic, practice_question, get_educational_videos, quick_answer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Per-user session: grade, age, subject, state, history
sessions = {}

def session(chat_id):
    if chat_id not in sessions:
        sessions[chat_id] = {
            "grade": None,
            "age": None,
            "subject": None,
            "state": "new",   # new | setup | ready
            "history": []
        }
    return sessions[chat_id]

# ── /start ────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sessions[chat_id] = {"grade": None, "age": None, "subject": None, "state": "ask_grade", "history": []}
    keyboard = [
        [InlineKeyboardButton(f"Grade {g}", callback_data=f"grade:{g}") for g in [6, 7, 8]],
        [InlineKeyboardButton(f"Grade {g}", callback_data=f"grade:{g}") for g in [9, 10, 11]],
        [InlineKeyboardButton("Grade 12", callback_data="grade:12")],
    ]
    await update.message.reply_text(
        "🎓 *Welcome to CodeVidhya AI Tutor!*\n\n"
        "Let's set up your profile. Please select your *Grade*:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ── /help ─────────────────────────────────────────────────────────────────────
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(update.effective_chat.id)
    subj = s["subject"] or "not set"
    grade = s["grade"]
    await update.message.reply_text(
        f"📋 *AI Tutor Help*\n\n"
        f"Current subject: *{subj}*\n"
        f"Current grade: *{grade}*\n\n"
        "*/subject [name]* — change subject\n"
        "  e.g. /subject Python\n"
        "  e.g. /subject Mathematics\n"
        "  e.g. /subject Spanish\n\n"
        "*/grade [1-12]* — change your grade\n"
        "  e.g. /grade 8\n\n"
        "*/topics* — list all topics for your subject\n\n"
        "*/explain [topic]* — full explanation with examples\n"
        "  e.g. /explain loops\n"
        "  e.g. /explain variables\n\n"
        "*/practice* — get a practice question\n\n"
        "*/videos* — get YouTube learning videos\n\n"
        "Or just type any question!",
        parse_mode="Markdown"
    )

# ── /grade ────────────────────────────────────────────────────────────────────
async def cmd_grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(update.effective_chat.id)
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /grade 8\nEnter your grade number (1-12)")
        return
    grade_num = args[0].replace("Grade", "").strip()
    s["grade"] = f"Grade {grade_num}"
    s["history"] = []
    await update.message.reply_text(
        f"✅ Grade set to *Grade {grade_num}*\n\n"
        f"Now set your subject with /subject [name]",
        parse_mode="Markdown"
    )

# ── /subject ──────────────────────────────────────────────────────────────────
async def cmd_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(update.effective_chat.id)
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /subject Python\n\n"
            "Examples:\n"
            "• /subject Python\n"
            "• /subject Mathematics\n"
            "• /subject Spanish\n"
            "• /subject Science\n"
            "• /subject English"
        )
        return
    subject = " ".join(args)
    s["subject"] = subject
    s["history"] = []
    await update.message.reply_text(
        f"✅ Subject set to *{subject}*\n\n"
        f"Type /topics to see all learning topics!",
        parse_mode="Markdown"
    )

# ── /topics ───────────────────────────────────────────────────────────────────
async def cmd_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(update.effective_chat.id)
    if not s["subject"]:
        await update.message.reply_text("Please set a subject first!\nExample: /subject Python")
        return
    await update.message.reply_text(f"⏳ Getting topics for *{s['subject']}*...", parse_mode="Markdown")
    try:
        result = get_topics(s["subject"], s["grade"])
        topics = result.get("topics", [])
        if not topics:
            await update.message.reply_text("No topics found. Try a different subject.")
            return
        text = f"📚 *{s['subject']} Topics* ({s['grade']})\n\n"
        for i, t in enumerate(topics, 1):
            text += f"{i}. {t}\n"
        text += f"\n💡 Type /explain [topic name] to start learning!\nExample: /explain {topics[0]}"
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error getting topics: {str(e)}")

# ── /explain ──────────────────────────────────────────────────────────────────
async def cmd_explain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(update.effective_chat.id)
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /explain [topic]\nExample: /explain loops")
        return
    topic = " ".join(args)
    subject = s["subject"] or "Programming"
    await update.message.reply_text(f"📖 Explaining *{topic}*...", parse_mode="Markdown")
    try:
        result = explain_topic(topic, s["grade"], subject, s["history"])
        explanation = result.get("explanation", "No explanation available.")
        # Telegram message limit is 4096 chars — split if needed
        if len(explanation) > 4000:
            explanation = explanation[:4000] + "...\n\n[Explanation truncated]"
        keyboard = [
            [InlineKeyboardButton("📝 Practice Question", callback_data=f"practice")],
            [InlineKeyboardButton("🎥 Watch Videos", callback_data=f"videos:{topic}")],
        ]
        await update.message.reply_text(
            f"📖 *{topic}*\n\n{explanation}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # Keep conversation history
        s["history"].append({"role": "user", "content": f"Explain {topic}"})
        s["history"].append({"role": "assistant", "content": explanation})
        s["history"] = s["history"][-10:]  # keep last 5 exchanges
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# ── /practice ─────────────────────────────────────────────────────────────────
async def cmd_practice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(update.effective_chat.id)
    subject = s["subject"] or "Python"
    await update.message.reply_text(f"📝 Generating practice question for *{subject}*...", parse_mode="Markdown")
    try:
        result = practice_question(subject, s["grade"])
        question = result.get("question", "No question generated.")
        await update.message.reply_text(
            f"📝 *Practice Question*\n\n{question}\n\n"
            f"💬 Type your answer or ask for a hint!",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# ── /videos ───────────────────────────────────────────────────────────────────
async def cmd_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(update.effective_chat.id)
    subject = s["subject"] or "Python"
    topic = " ".join(context.args) if context.args else None
    await update.message.reply_text(f"🎥 Finding videos for *{subject}*...", parse_mode="Markdown")
    try:
        result = get_educational_videos(subject, s["grade"], topic)
        videos = result.get("videos", [])
        if not videos:
            await update.message.reply_text("No videos found. Try /videos [topic name]")
            return
        text = f"🎥 *Learning Videos — {subject}*\n\n"
        for v in videos[:5]:
            title = v.get("title", "Video")
            url = v.get("url", "")
            text += f"▶️ [{title}]({url})\n\n"
        await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=False)
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# ── Free text handler ─────────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    s = session(chat_id)
    text = update.message.text.strip()

    # ── SETUP: student typed custom subject ──────────────────────────────────
    if s["state"] == "ask_subject_text":
        await _finish_setup(update.message, s, text)
        return

    # ── OLD SETUP STATE (fallback) ────────────────────────────────────────────
    if s["state"] == "setup":
        try:
            # Parse: "Grade 8, 13, Python" or "8, 13, Python" or similar
            parts = [p.strip() for p in text.replace(";", ",").split(",")]
            grade_raw = parts[0] if len(parts) > 0 else "8"
            age_raw   = parts[1] if len(parts) > 1 else "13"
            subject   = parts[2] if len(parts) > 2 else "Python"

            # Clean grade
            grade_num = grade_raw.lower().replace("grade", "").strip()
            grade = f"Grade {grade_num}"

            # Clean age
            age = age_raw.replace("years", "").replace("yr", "").strip()

            s["grade"]   = grade
            s["age"]     = age
            s["subject"] = subject
            s["state"]   = "ready"

            await update.message.reply_text(
                f"✅ *Got it!*\n\n"
                f"👤 Age: *{age}*\n"
                f"📚 Grade: *{grade}*\n"
                f"🎯 Subject: *{subject}*\n\n"
                f"Loading your topics...",
                parse_mode="Markdown"
            )

            # Auto-load topics
            result = get_topics(subject, grade)
            topics = result.get("topics", [])
            if topics:
                text_topics = f"📚 *{subject} Topics for {grade}*\n\n"
                for i, t in enumerate(topics, 1):
                    text_topics += f"{i}. {t}\n"
                text_topics += f"\n💡 Type /explain [topic] to start!\nExample: `/explain {topics[0]}`"
                await update.message.reply_text(text_topics, parse_mode="Markdown")
            else:
                await update.message.reply_text(f"Ready! Ask me anything about {subject} 🚀")
        except Exception as e:
            await update.message.reply_text(
                "❌ I couldn't understand that. Please reply like this:\n\n"
                "`Grade 8, 13, Python`\n\n"
                "Format: Grade, Age, Subject",
                parse_mode="Markdown"
            )
        return

    # ── READY STATE: answer questions ─────────────────────────────────────────
    if s["state"] != "ready":
        await update.message.reply_text("Please type /start to begin.")
        return

    await update.message.reply_text("🤔 Thinking...")
    try:
        result = quick_answer(text, s["grade"] or "Grade 8")
        answer = result.get("answer", "I couldn't find an answer.")
        if len(answer) > 4000:
            answer = answer[:4000] + "..."
        s["history"].append({"role": "user", "content": text})
        s["history"].append({"role": "assistant", "content": answer})
        s["history"] = s["history"][-10:]
        keyboard = [[InlineKeyboardButton("📝 Practice Question", callback_data="practice")]]
        await update.message.reply_text(
            answer,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# ── Inline button callbacks ───────────────────────────────────────────────────
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    s = session(chat_id)
    data = query.data

    # ── FORM: Grade selected ──────────────────────────────────────────────────
    if data.startswith("grade:"):
        grade_num = data.split(":")[1]
        s["grade"] = f"Grade {grade_num}"
        s["state"] = "ask_age"
        keyboard = [
            [InlineKeyboardButton(str(a), callback_data=f"age:{a}") for a in [11, 12, 13, 14]],
            [InlineKeyboardButton(str(a), callback_data=f"age:{a}") for a in [15, 16, 17, 18]],
            [InlineKeyboardButton("18+", callback_data="age:18+")],
        ]
        await query.message.reply_text(
            f"✅ Grade *{grade_num}* selected!\n\n"
            f"Now select your *Age*:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── FORM: Age selected ────────────────────────────────────────────────────
    elif data.startswith("age:"):
        age = data.split(":")[1]
        s["age"] = age
        s["state"] = "ask_subject"
        keyboard = [
            [InlineKeyboardButton("🐍 Python",      callback_data="subject:Python"),
             InlineKeyboardButton("📐 Mathematics",  callback_data="subject:Mathematics")],
            [InlineKeyboardButton("🔬 Science",      callback_data="subject:Science"),
             InlineKeyboardButton("📖 English",      callback_data="subject:English")],
            [InlineKeyboardButton("🌍 Spanish",      callback_data="subject:Spanish"),
             InlineKeyboardButton("💻 JavaScript",   callback_data="subject:JavaScript")],
            [InlineKeyboardButton("🤖 AI & ML",      callback_data="subject:AI and Machine Learning"),
             InlineKeyboardButton("📊 Data Science", callback_data="subject:Data Science")],
            [InlineKeyboardButton("✏️ Other (type below)", callback_data="subject:other")],
        ]
        await query.message.reply_text(
            f"✅ Age *{age}* selected!\n\n"
            f"Now select your *Subject*:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ── FORM: Subject selected ────────────────────────────────────────────────
    elif data.startswith("subject:"):
        subject = data.split(":", 1)[1]
        if subject == "other":
            s["state"] = "ask_subject_text"
            await query.message.reply_text(
                "✏️ Type your subject name below:",
                parse_mode="Markdown"
            )
            return
        await _finish_setup(query.message, s, subject)

    # ── LEARNING: Practice question ───────────────────────────────────────────
    elif data == "practice":
        subject = s["subject"] or "Python"
        await query.message.reply_text(f"📝 Generating practice question for *{subject}*...", parse_mode="Markdown")
        try:
            result = practice_question(subject, s["grade"])
            question = result.get("question", "No question generated.")
            await query.message.reply_text(f"📝 *Practice Question*\n\n{question}", parse_mode="Markdown")
        except Exception as e:
            await query.message.reply_text(f"Error: {str(e)}")

    # ── LEARNING: Videos ──────────────────────────────────────────────────────
    elif data.startswith("videos:"):
        topic = data.split(":", 1)[1]
        subject = s["subject"] or "Python"
        try:
            result = get_educational_videos(subject, s["grade"], topic)
            videos = result.get("videos", [])
            if not videos:
                await query.message.reply_text("No videos found.")
                return
            text = f"🎥 *Videos — {topic}*\n\n"
            for v in videos[:5]:
                text += f"▶️ [{v.get('title','Video')}]({v.get('url','')})\n\n"
            await query.message.reply_text(text, parse_mode="Markdown")
        except Exception as e:
            await query.message.reply_text(f"Error: {str(e)}")

# ── Shared: finish setup and load topics ──────────────────────────────────────
async def _finish_setup(message, s: dict, subject: str):
    s["subject"] = subject
    s["state"]   = "ready"
    await message.reply_text(
        f"🎉 *All set!*\n\n"
        f"👤 Age: *{s['age']}*\n"
        f"📚 Grade: *{s['grade']}*\n"
        f"🎯 Subject: *{subject}*\n\n"
        f"Loading your topics...",
        parse_mode="Markdown"
    )
    try:
        result = get_topics(subject, s["grade"])
        topics = result.get("topics", [])
        if topics:
            text = f"📚 *{subject} Topics — {s['grade']}*\n\n"
            for i, t in enumerate(topics, 1):
                text += f"{i}. {t}\n"
            text += f"\n💡 Type /explain [topic] to start learning!\nExample: `/explain {topics[0]}`"
            await message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await message.reply_text(f"Ready to learn {subject}! Ask me anything. 🚀")

# ── Start bot (runs in background thread) ─────────────────────────────────────
def run():
    if not BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled")
        return

    async def _main():
        app = Application.builder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start",    cmd_start))
        app.add_handler(CommandHandler("help",     cmd_help))
        app.add_handler(CommandHandler("grade",    cmd_grade))
        app.add_handler(CommandHandler("subject",  cmd_subject))
        app.add_handler(CommandHandler("topics",   cmd_topics))
        app.add_handler(CommandHandler("explain",  cmd_explain))
        app.add_handler(CommandHandler("practice", cmd_practice))
        app.add_handler(CommandHandler("videos",   cmd_videos))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        logger.info("🤖 Telegram AI Tutor Bot started!")
        async with app:
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            await asyncio.Event().wait()  # run forever

    asyncio.run(_main())

def start():
    t = threading.Thread(target=run, daemon=True)
    t.start()
