#!/usr/bin/env python3
"""
CodeVidhya AI Tutor — Telegram Bot (webhook mode, fully button-based)
Students never need to type — all interactions are tap buttons.
"""

import os
import re
import asyncio
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

# Per-user sessions
sessions: dict = {}

def session(chat_id):
    if chat_id not in sessions:
        sessions[chat_id] = {
            "grade": None,
            "age": None,
            "subject": None,
            "state": "ask_grade",
            "topics": [],
            "current_topic": None,
            "qa_questions": [],
            "practice_data": {},
            "history": [],
        }
    return sessions[chat_id]

# ── Async wrappers for sync MCP calls ─────────────────────────────────────────
async def _get_topics(subject, grade):
    return await asyncio.to_thread(get_topics, subject, grade)

async def _explain(topic, grade, subject, history):
    return await asyncio.to_thread(explain_topic, topic, grade, subject, history)

async def _practice(subject, grade):
    return await asyncio.to_thread(practice_question, subject, grade)

async def _videos(subject, grade, topic):
    return await asyncio.to_thread(get_educational_videos, subject, grade, topic)

async def _quick(question, grade):
    return await asyncio.to_thread(quick_answer, question, grade)

# ── Keyboards ──────────────────────────────────────────────────────────────────

def kb_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Topics",          callback_data="m:topics"),
         InlineKeyboardButton("📖 Explain Topic",   callback_data="m:explain")],
        [InlineKeyboardButton("📝 Practice Quiz",   callback_data="m:practice"),
         InlineKeyboardButton("🎥 Watch Videos",    callback_data="m:videos")],
        [InlineKeyboardButton("💬 Ask a Question",  callback_data="m:qa")],
        [InlineKeyboardButton("📊 Change Grade",    callback_data="m:grade"),
         InlineKeyboardButton("🔄 Change Subject",  callback_data="m:subject")],
    ])

def kb_grades():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Grade {g}", callback_data=f"grade:{g}") for g in [6, 7, 8]],
        [InlineKeyboardButton(f"Grade {g}", callback_data=f"grade:{g}") for g in [9, 10, 11]],
        [InlineKeyboardButton("Grade 12", callback_data="grade:12")],
    ])

def kb_ages():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(str(a), callback_data=f"age:{a}") for a in [11, 12, 13, 14]],
        [InlineKeyboardButton(str(a), callback_data=f"age:{a}") for a in [15, 16, 17, 18]],
        [InlineKeyboardButton("18+", callback_data="age:18+")],
    ])

def kb_subjects():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🐍 Python",     callback_data="subject:Python"),
         InlineKeyboardButton("📐 Mathematics", callback_data="subject:Mathematics")],
        [InlineKeyboardButton("🔬 Science",    callback_data="subject:Science"),
         InlineKeyboardButton("📖 English",    callback_data="subject:English")],
        [InlineKeyboardButton("🌍 Spanish",    callback_data="subject:Spanish"),
         InlineKeyboardButton("💻 JavaScript", callback_data="subject:JavaScript")],
        [InlineKeyboardButton("🤖 AI & ML",    callback_data="subject:AI and Machine Learning"),
         InlineKeyboardButton("📊 Data Science", callback_data="subject:Data Science")],
    ])

def kb_topics(topics, prefix):
    rows = []
    for i in range(0, len(topics), 2):
        row = [InlineKeyboardButton(f"📌 {topics[i]}", callback_data=f"{prefix}:{i}")]
        if i + 1 < len(topics):
            row.append(InlineKeyboardButton(f"📌 {topics[i+1]}", callback_data=f"{prefix}:{i+1}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def kb_after_explain():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Practice on this", callback_data="p:topic"),
         InlineKeyboardButton("🎥 Videos for this",  callback_data="v:topic")],
        [InlineKeyboardButton("💬 Ask a Question",   callback_data="qa:topic"),
         InlineKeyboardButton("🏠 Main Menu",        callback_data="home")],
    ])

def kb_after_practice():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Try Another",  callback_data="p:next"),
         InlineKeyboardButton("💡 Show Hint",    callback_data="p:hint")],
        [InlineKeyboardButton("✅ Show Answer",  callback_data="p:answer"),
         InlineKeyboardButton("🏠 Main Menu",    callback_data="home")],
    ])

def kb_mcq(options):
    rows = []
    for letter, text in options:
        label = f"{letter})  {text[:50]}"
        rows.append([InlineKeyboardButton(label, callback_data=f"mcq:{letter}")])
    rows.append([InlineKeyboardButton("💡 Hint",      callback_data="p:hint"),
                 InlineKeyboardButton("🏠 Main Menu", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def kb_qa(questions):
    rows = [[InlineKeyboardButton(f"❓ {q[:55]}", callback_data=f"qq:{i}")]
            for i, q in enumerate(questions)]
    rows.append([InlineKeyboardButton("🔄 More Questions", callback_data="qa:more"),
                 InlineKeyboardButton("🏠 Main Menu",      callback_data="home")])
    return InlineKeyboardMarkup(rows)

def kb_after_qa():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 More Questions", callback_data="qa:more"),
         InlineKeyboardButton("🏠 Main Menu",      callback_data="home")],
    ])

def kb_home():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="home")]])

def kb_next_practice():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Next Question", callback_data="p:next"),
         InlineKeyboardButton("🏠 Main Menu",     callback_data="home")],
    ])

# ── Helpers ────────────────────────────────────────────────────────────────────

def parse_mcq(text):
    """Extract MCQ stem and options from AI-generated question text."""
    lines = text.strip().split("\n")
    options, stem_lines = [], []
    for line in lines:
        m = re.match(r"^\s*([A-D])[.)]\s+(.+)", line)
        if m:
            options.append((m.group(1), m.group(2).strip()))
        else:
            stem_lines.append(line)
    return "\n".join(stem_lines).strip(), options

async def _gen_qa_questions(subject, grade, topic=None):
    context = f"{topic} in {subject}" if topic else subject
    prompt = (
        f"List exactly 6 short student questions about {context} for {grade}. "
        "Return only the questions, one per line, no numbering."
    )
    fallback = [
        f"What is {context}?",
        f"How does {context} work?",
        f"Give me an example of {context}.",
        f"Why is {context} important?",
        f"What are common mistakes with {context}?",
        f"How do I practice {context}?",
    ]
    try:
        result = await _quick(prompt, grade or "Grade 8")
        qs = [q.strip() for q in result.get("answer", "").split("\n") if q.strip()][:6]
        return qs if len(qs) >= 3 else fallback
    except Exception:
        return fallback

async def _send_main_menu(msg, s):
    await msg.reply_text(
        f"🏠 *Main Menu*\n\n"
        f"Grade: *{s['grade']}*  |  Subject: *{s['subject']}*\n\n"
        f"Tap what you want to do 👇",
        parse_mode="Markdown",
        reply_markup=kb_main_menu(),
    )

async def _fetch_and_show_topics(msg, s, prefix):
    await msg.reply_text(f"⏳ Loading *{s['subject']}* topics...", parse_mode="Markdown")
    result = await _get_topics(s["subject"], s["grade"])
    topics = result.get("topics", [])
    if not topics:
        await msg.reply_text("No topics found for this subject.", reply_markup=kb_home())
        return False
    s["topics"] = topics
    return True

# ── /start ─────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    sessions[chat_id] = {
        "grade": None, "age": None, "subject": None,
        "state": "ask_grade", "topics": [], "current_topic": None,
        "qa_questions": [], "practice_data": {}, "history": [],
    }
    await update.message.reply_text(
        "🎓 *Welcome to CodeVidhya AI Tutor!*\n\n"
        "Your personal AI teacher on Telegram.\n"
        "Everything works with *tap buttons* — no typing needed!\n\n"
        "Let's start. Select your *Grade* 👇",
        parse_mode="Markdown",
        reply_markup=kb_grades(),
    )

# ── Callback handler ───────────────────────────────────────────────────────────
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    s = session(chat_id)
    data = query.data
    msg = query.message

    # ── ONBOARDING ─────────────────────────────────────────────────────────────

    if data.startswith("grade:"):
        grade_num = data.split(":")[1]
        s["grade"] = f"Grade {grade_num}"
        s["history"] = []
        await msg.reply_text(
            f"✅ *Grade {grade_num}* selected!\n\nHow old are you? 👇",
            parse_mode="Markdown",
            reply_markup=kb_ages(),
        )

    elif data.startswith("age:"):
        s["age"] = data.split(":")[1]
        await msg.reply_text(
            f"✅ Age *{s['age']}* noted!\n\nChoose your *Subject* 👇",
            parse_mode="Markdown",
            reply_markup=kb_subjects(),
        )

    elif data.startswith("subject:"):
        subject = data.split(":", 1)[1]
        s["subject"] = subject
        s["state"] = "ready"
        s["topics"] = []
        s["current_topic"] = None
        await msg.reply_text(
            f"🎉 *All set!*\n\n"
            f"Grade: *{s['grade']}*  |  Subject: *{subject}*\n\n"
            f"Tap any button to start learning! 👇",
            parse_mode="Markdown",
            reply_markup=kb_main_menu(),
        )

    # ── NAVIGATION ─────────────────────────────────────────────────────────────

    elif data == "home":
        if not s["subject"]:
            await msg.reply_text("Let's set up first! Select your Grade:", reply_markup=kb_grades())
        else:
            await _send_main_menu(msg, s)

    elif data == "m:grade":
        await msg.reply_text("Select your *Grade* 👇", parse_mode="Markdown", reply_markup=kb_grades())

    elif data == "m:subject":
        await msg.reply_text("Select your *Subject* 👇", parse_mode="Markdown", reply_markup=kb_subjects())

    # ── TOPICS ─────────────────────────────────────────────────────────────────

    elif data == "m:topics":
        ok = await _fetch_and_show_topics(msg, s, "topic")
        if ok:
            await msg.reply_text(
                f"📚 *{s['subject']} Topics — {s['grade']}*\n\nTap a topic to explore it:",
                parse_mode="Markdown",
                reply_markup=kb_topics(s["topics"], "topic"),
            )

    elif data.startswith("topic:"):
        idx = int(data.split(":")[1])
        if 0 <= idx < len(s["topics"]):
            s["current_topic"] = s["topics"][idx]
            await _do_explain(msg, s)

    # ── EXPLAIN ────────────────────────────────────────────────────────────────

    elif data == "m:explain":
        ok = await _fetch_and_show_topics(msg, s, "explain")
        if ok:
            await msg.reply_text(
                f"📖 *Which topic to explain?*\n\nTap a topic:",
                parse_mode="Markdown",
                reply_markup=kb_topics(s["topics"], "explain"),
            )

    elif data.startswith("explain:"):
        idx = int(data.split(":")[1])
        if 0 <= idx < len(s["topics"]):
            s["current_topic"] = s["topics"][idx]
            await _do_explain(msg, s)

    # ── PRACTICE ───────────────────────────────────────────────────────────────

    elif data in ("m:practice", "p:topic", "p:next"):
        await _do_practice(msg, s)

    elif data == "p:hint":
        hint = s["practice_data"].get("hint") or "Break the problem into smaller steps. Re-read the question carefully!"
        await msg.reply_text(f"💡 *Hint*\n\n{hint}", parse_mode="Markdown",
                             reply_markup=kb_after_practice())

    elif data == "p:answer":
        answer = s["practice_data"].get("answer", "")
        if not answer:
            q = s["practice_data"].get("question", "")
            try:
                res = await _quick(f"Answer this question: {q}", s["grade"])
                answer = res.get("answer", "Sorry, I couldn't generate the answer.")
            except Exception:
                answer = "Please try another question."
        await msg.reply_text(f"✅ *Answer*\n\n{answer}", parse_mode="Markdown",
                             reply_markup=kb_after_practice())

    elif data.startswith("mcq:"):
        letter = data.split(":")[1]
        correct = s["practice_data"].get("correct", "")
        if correct and letter == correct:
            await msg.reply_text(
                f"🎉 *Correct! '{letter}' is right!*\n\nExcellent work! Ready for the next one?",
                parse_mode="Markdown",
                reply_markup=kb_next_practice(),
            )
        elif correct:
            await msg.reply_text(
                f"❌ Not quite! The correct answer is *{correct}*.\n\nKeep practicing — you've got this!",
                parse_mode="Markdown",
                reply_markup=kb_next_practice(),
            )
        else:
            await msg.reply_text(
                f"You selected *{letter}*.",
                parse_mode="Markdown",
                reply_markup=kb_after_practice(),
            )

    # ── VIDEOS ─────────────────────────────────────────────────────────────────

    elif data == "m:videos":
        ok = await _fetch_and_show_topics(msg, s, "vtopic")
        if ok:
            await msg.reply_text(
                f"🎥 *Which topic's videos?*\n\nTap a topic:",
                parse_mode="Markdown",
                reply_markup=kb_topics(s["topics"], "vtopic"),
            )

    elif data.startswith("vtopic:"):
        idx = int(data.split(":")[1])
        if 0 <= idx < len(s["topics"]):
            s["current_topic"] = s["topics"][idx]
            await _do_videos(msg, s)

    elif data == "v:topic":
        await _do_videos(msg, s)

    # ── Q&A ────────────────────────────────────────────────────────────────────

    elif data in ("m:qa", "qa:topic", "qa:more"):
        await _do_qa(msg, s)

    elif data.startswith("qq:"):
        idx = int(data.split(":")[1])
        qs = s.get("qa_questions", [])
        if 0 <= idx < len(qs):
            question = qs[idx]
            await msg.reply_text(f"⏳ _{question}_", parse_mode="Markdown")
            try:
                res = await _quick(question, s["grade"] or "Grade 8")
                answer = res.get("answer", "Sorry, I couldn't answer that.")
                if len(answer) > 3800:
                    answer = answer[:3800] + "..."
                await msg.reply_text(answer, parse_mode="Markdown", reply_markup=kb_after_qa())
            except Exception:
                await msg.reply_text("Error getting answer.", reply_markup=kb_after_qa())

# ── Action helpers ─────────────────────────────────────────────────────────────

async def _do_explain(msg, s):
    topic = s["current_topic"]
    await msg.reply_text(f"📖 Explaining *{topic}*...", parse_mode="Markdown")
    try:
        result = await _explain(topic, s["grade"], s["subject"], s["history"])
        explanation = result.get("explanation", "No explanation available.")
        if len(explanation) > 3800:
            explanation = explanation[:3800] + "..."
        s["history"].append({"role": "user", "content": f"Explain {topic}"})
        s["history"].append({"role": "assistant", "content": explanation})
        s["history"] = s["history"][-10:]
        await msg.reply_text(
            f"📖 *{topic}*\n\n{explanation}",
            parse_mode="Markdown",
            reply_markup=kb_after_explain(),
        )
    except Exception as e:
        logger.error(f"explain error: {e}")
        await msg.reply_text("Error explaining topic.", reply_markup=kb_home())

async def _do_practice(msg, s):
    subject = s["subject"] or "Python"
    await msg.reply_text(f"📝 Generating practice question for *{subject}*...", parse_mode="Markdown")
    try:
        result = await _practice(subject, s["grade"])
        q_text = result.get("question", "No question generated.")

        stem, options = parse_mcq(q_text)

        if len(options) >= 2:
            # Find embedded correct answer marker, strip it from stem
            correct_m = re.search(r"(?:correct answer|answer)[:\s]+([A-D])", q_text, re.IGNORECASE)
            correct = correct_m.group(1).upper() if correct_m else ""
            clean_stem = re.sub(r"\n?(?:correct answer|answer)[:\s]+[A-D].*", "", stem, flags=re.IGNORECASE).strip()
            s["practice_data"] = {"question": q_text, "answer": correct, "correct": correct, "hint": ""}
            await msg.reply_text(
                f"📝 *Practice Question*\n\n{clean_stem}\n\n_Tap the correct answer:_",
                parse_mode="Markdown",
                reply_markup=kb_mcq(options),
            )
        else:
            s["practice_data"] = {"question": q_text, "answer": "", "correct": "", "hint": ""}
            await msg.reply_text(
                f"📝 *Practice Question*\n\n{q_text}",
                parse_mode="Markdown",
                reply_markup=kb_after_practice(),
            )
    except Exception as e:
        logger.error(f"practice error: {e}")
        await msg.reply_text("Error generating question.", reply_markup=kb_home())

async def _do_videos(msg, s):
    topic = s["current_topic"]
    subject = s["subject"] or "Python"
    label = topic or subject
    await msg.reply_text(f"🎥 Finding videos for *{label}*...", parse_mode="Markdown")
    try:
        result = await _videos(subject, s["grade"], topic)
        videos = result.get("videos", [])
        if not videos:
            await msg.reply_text("No videos found for this topic.", reply_markup=kb_home())
            return
        text = f"🎥 *Learning Videos*\n_{label}_\n\n"
        for v in videos[:5]:
            title = v.get("title", "Video")
            url = v.get("url", "")
            text += f"▶️ [{title}]({url})\n\n"
        await msg.reply_text(text, parse_mode="Markdown",
                             disable_web_page_preview=False, reply_markup=kb_home())
    except Exception as e:
        logger.error(f"videos error: {e}")
        await msg.reply_text("Error fetching videos.", reply_markup=kb_home())

async def _do_qa(msg, s):
    topic = s["current_topic"]
    subject = s["subject"] or "Python"
    label = f"*{topic}*" if topic else f"*{subject}*"
    await msg.reply_text(f"⏳ Generating questions for {label}...", parse_mode="Markdown")
    questions = await _gen_qa_questions(subject, s["grade"], topic)
    s["qa_questions"] = questions
    await msg.reply_text(
        f"💬 *Common Questions — {label}*\n\nTap a question to get the answer:",
        parse_mode="Markdown",
        reply_markup=kb_qa(questions),
    )

# ── Text guard (no typing needed) ─────────────────────────────────────────────
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = session(update.effective_chat.id)
    if not s["subject"]:
        await update.message.reply_text(
            "👆 Tap a button above to continue setup.",
        )
    else:
        await update.message.reply_text(
            "👆 Use the buttons to navigate — no typing needed!",
            reply_markup=kb_main_menu(),
        )

# ── Build PTB Application (called once from app.py startup) ───────────────────
def create_application():
    if not BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled")
        return None
    ptb = Application.builder().token(BOT_TOKEN).build()
    ptb.add_handler(CommandHandler("start", cmd_start))
    ptb.add_handler(CallbackQueryHandler(handle_callback))
    ptb.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    return ptb
