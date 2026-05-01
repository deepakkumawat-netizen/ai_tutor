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

# Per-user session: grade, subject, history
sessions = {}

def session(chat_id):
    if chat_id not in sessions:
        sessions[chat_id] = {"grade": "Grade 8", "subject": None, "history": []}
    return sessions[chat_id]

# ── /start ────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎓 *Welcome to CodeVidhya AI Tutor!*\n\n"
        "I can teach you any subject with explanations, practice questions and videos.\n\n"
        "📚 *Commands:*\n"
        "/subject python — set subject\n"
        "/grade 8 — set your grade\n"
        "/topics — see all topics\n"
        "/explain loops — explain a topic\n"
        "/practice — get a practice question\n"
        "/videos — get learning videos\n"
        "/help — show this menu\n\n"
        "Or just *type any question* and I'll answer it! 💡",
        parse_mode="Markdown"
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

# ── Free text → quick_answer ──────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(update.effective_chat.id)
    question = update.message.text.strip()
    await update.message.reply_text("🤔 Thinking...")
    try:
        result = quick_answer(question, s["grade"])
        answer = result.get("answer", "I couldn't find an answer.")
        if len(answer) > 4000:
            answer = answer[:4000] + "..."
        s["history"].append({"role": "user", "content": question})
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
    s = session(query.message.chat_id)
    data = query.data

    if data == "practice":
        subject = s["subject"] or "Python"
        await query.message.reply_text(f"📝 Generating practice question for *{subject}*...", parse_mode="Markdown")
        try:
            result = practice_question(subject, s["grade"])
            question = result.get("question", "No question generated.")
            await query.message.reply_text(f"📝 *Practice Question*\n\n{question}", parse_mode="Markdown")
        except Exception as e:
            await query.message.reply_text(f"Error: {str(e)}")

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

# ── Start bot (runs in background thread) ─────────────────────────────────────
def run():
    if not BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled")
        return
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("grade", cmd_grade))
    app.add_handler(CommandHandler("subject", cmd_subject))
    app.add_handler(CommandHandler("topics", cmd_topics))
    app.add_handler(CommandHandler("explain", cmd_explain))
    app.add_handler(CommandHandler("practice", cmd_practice))
    app.add_handler(CommandHandler("videos", cmd_videos))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🤖 Telegram AI Tutor Bot started!")
    app.run_polling(drop_pending_updates=True)

def start():
    t = threading.Thread(target=run, daemon=True)
    t.start()
