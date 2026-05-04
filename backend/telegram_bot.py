#!/usr/bin/env python3
"""
CodeVidhya AI Tutor — Telegram Bot (K-12, webhook, fully button-driven)
Uses NLP engine for grade-adaptive, sentiment-aware responses.
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
from nlp_engine import nlp_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

sessions: dict = {}

# ── Grade configuration (K-12) ─────────────────────────────────────────────────
GRADE_CONFIG = {
    "Kindergarten": {
        "emoji": "🌟", "short": "K",
        "style": "Use very simple words a 5-year-old understands. Use fun stories and colorful examples. Very short sentences. Add fun emojis.",
        "encourage": "🌟 Amazing job! You're doing great, superstar!",
        "hint_style": "Think of it like a fun game! 🎮",
    },
    "Grade 1": {
        "emoji": "⭐", "short": "1",
        "style": "Use very simple words and short sentences. Give fun real-life examples. Use emojis to make it exciting.",
        "encourage": "⭐ Excellent! You're so smart!",
        "hint_style": "Here's a clue to help you! 💡",
    },
    "Grade 2": {
        "emoji": "🌈", "short": "2",
        "style": "Use simple clear language with relatable examples. Keep explanations short and engaging.",
        "encourage": "🌈 Great work! Keep it up!",
        "hint_style": "Here's a little hint! 🔍",
    },
    "Grade 3": {
        "emoji": "🦋", "short": "3",
        "style": "Use clear simple language with real-world examples. Introduce basic terms gently.",
        "encourage": "🦋 Wonderful effort! You're learning fast!",
        "hint_style": "Let's think about it together 🤔",
    },
    "Grade 4": {
        "emoji": "🚀", "short": "4",
        "style": "Use clear explanations with interesting examples. Introduce proper terms with simple definitions.",
        "encourage": "🚀 Fantastic! You're on a learning rocket!",
        "hint_style": "Here's a clue to point you in the right direction 🎯",
    },
    "Grade 5": {
        "emoji": "💡", "short": "5",
        "style": "Use clear structured explanations with practical examples and step-by-step breakdowns.",
        "encourage": "💡 Brilliant work! Your knowledge is growing!",
        "hint_style": "Think step by step 🪜",
    },
    "Grade 6": {
        "emoji": "🔬", "short": "6",
        "style": "Use structured explanations with proper terminology and relevant examples.",
        "encourage": "🔬 Excellent work! You're a true learner!",
        "hint_style": "Break it down into smaller parts 🧩",
    },
    "Grade 7": {
        "emoji": "📐", "short": "7",
        "style": "Use proper terminology with clear explanations and real-world applications.",
        "encourage": "📐 Great job! Your understanding is impressive!",
        "hint_style": "Consider the key concepts 🔑",
    },
    "Grade 8": {
        "emoji": "🧮", "short": "8",
        "style": "Provide detailed explanations using proper academic terminology with examples.",
        "encourage": "🧮 Outstanding! You're mastering this!",
        "hint_style": "Think about the underlying concept 💭",
    },
    "Grade 9": {
        "emoji": "⚗️", "short": "9",
        "style": "Use academic language with comprehensive explanations and practical applications.",
        "encourage": "⚗️ Excellent analytical thinking!",
        "hint_style": "Apply the core principles you've learned 📚",
    },
    "Grade 10": {
        "emoji": "🎯", "short": "10",
        "style": "Provide comprehensive explanations with technical depth and real-world applications.",
        "encourage": "🎯 Superb! Your advanced thinking shows!",
        "hint_style": "Consider both the theory and its application 🔭",
    },
    "Grade 11": {
        "emoji": "📊", "short": "11",
        "style": "Use advanced academic language with in-depth analysis and complex examples.",
        "encourage": "📊 Impressive advanced understanding!",
        "hint_style": "Think analytically and systematically 🧠",
    },
    "Grade 12": {
        "emoji": "🏆", "short": "12",
        "style": "Use college-prep level explanations with comprehensive depth and advanced terminology.",
        "encourage": "🏆 Exceptional! College-level thinking!",
        "hint_style": "Apply your comprehensive knowledge base 🎓",
    },
}

def grade_emoji(grade):
    return GRADE_CONFIG.get(grade, {}).get("emoji", "📚")

def grade_style(grade):
    return GRADE_CONFIG.get(grade, {}).get("style", "Use clear explanations with examples.")

def grade_encourage(grade):
    return GRADE_CONFIG.get(grade, {}).get("encourage", "✅ Great job! Keep learning!")

# ── Session ────────────────────────────────────────────────────────────────────
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
            # Flashcards
            "flashcards": [],
            "fc_idx": 0,
            # Test
            "test_questions": [],
            "test_idx": 0,
            "test_score": 0,
            # Progress tracking
            "lessons_done": 0,
            "practice_total": 0,
            "practice_correct": 0,
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

async def _nlp_analyze(question, context=""):
    return await asyncio.to_thread(nlp_engine.analyze_question, question, context)

async def _nlp_strategy(question):
    return await asyncio.to_thread(nlp_engine.classify_question_type, question)

# ── Keyboards ──────────────────────────────────────────────────────────────────
def kb_grades():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌟 Kindergarten", callback_data="grade:Kindergarten")],
        [InlineKeyboardButton("Grade 1", callback_data="grade:1"),
         InlineKeyboardButton("Grade 2", callback_data="grade:2"),
         InlineKeyboardButton("Grade 3", callback_data="grade:3")],
        [InlineKeyboardButton("Grade 4", callback_data="grade:4"),
         InlineKeyboardButton("Grade 5", callback_data="grade:5"),
         InlineKeyboardButton("Grade 6", callback_data="grade:6")],
        [InlineKeyboardButton("Grade 7", callback_data="grade:7"),
         InlineKeyboardButton("Grade 8", callback_data="grade:8"),
         InlineKeyboardButton("Grade 9", callback_data="grade:9")],
        [InlineKeyboardButton("Grade 10", callback_data="grade:10"),
         InlineKeyboardButton("Grade 11", callback_data="grade:11"),
         InlineKeyboardButton("Grade 12", callback_data="grade:12")],
    ])

def kb_ages():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("4",  callback_data="age:4"),
         InlineKeyboardButton("5",  callback_data="age:5"),
         InlineKeyboardButton("6",  callback_data="age:6"),
         InlineKeyboardButton("7",  callback_data="age:7")],
        [InlineKeyboardButton("8",  callback_data="age:8"),
         InlineKeyboardButton("9",  callback_data="age:9"),
         InlineKeyboardButton("10", callback_data="age:10"),
         InlineKeyboardButton("11", callback_data="age:11")],
        [InlineKeyboardButton("12", callback_data="age:12"),
         InlineKeyboardButton("13", callback_data="age:13"),
         InlineKeyboardButton("14", callback_data="age:14"),
         InlineKeyboardButton("15", callback_data="age:15")],
        [InlineKeyboardButton("16", callback_data="age:16"),
         InlineKeyboardButton("17", callback_data="age:17"),
         InlineKeyboardButton("18", callback_data="age:18"),
         InlineKeyboardButton("18+", callback_data="age:18+")],
    ])

def kb_subjects():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🐍 Python",      callback_data="subject:Python"),
         InlineKeyboardButton("📐 Mathematics", callback_data="subject:Mathematics")],
        [InlineKeyboardButton("🔬 Science",     callback_data="subject:Science"),
         InlineKeyboardButton("📖 English",     callback_data="subject:English")],
        [InlineKeyboardButton("🌍 Spanish",     callback_data="subject:Spanish"),
         InlineKeyboardButton("💻 JavaScript",  callback_data="subject:JavaScript")],
        [InlineKeyboardButton("🤖 AI & ML",     callback_data="subject:AI and Machine Learning"),
         InlineKeyboardButton("📊 Data Science",callback_data="subject:Data Science")],
        [InlineKeyboardButton("🎨 Art & Craft", callback_data="subject:Art and Craft"),
         InlineKeyboardButton("🌿 Environment", callback_data="subject:Environmental Science")],
        [InlineKeyboardButton("🔍 Search Any Subject", callback_data="subject:_other")],
    ])

def kb_main_menu(grade=None):
    emoji = grade_emoji(grade) if grade else "📚"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Topics",          callback_data="m:topics"),
         InlineKeyboardButton("📖 Explain",         callback_data="m:explain")],
        [InlineKeyboardButton("🃏 Flashcards",      callback_data="m:flashcards"),
         InlineKeyboardButton("🧪 Take Test",       callback_data="m:test")],
        [InlineKeyboardButton("📝 Practice Quiz",   callback_data="m:practice"),
         InlineKeyboardButton("🎥 Videos",          callback_data="m:videos")],
        [InlineKeyboardButton("💬 Ask a Question",  callback_data="m:qa")],
        [InlineKeyboardButton("📊 My Progress",     callback_data="m:progress")],
        [InlineKeyboardButton("🎓 Change Grade",    callback_data="m:grade"),
         InlineKeyboardButton("🔄 Change Subject",  callback_data="m:subject")],
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
        [InlineKeyboardButton("📝 Practice on This", callback_data="p:topic"),
         InlineKeyboardButton("🎥 Videos for This",  callback_data="v:topic")],
        [InlineKeyboardButton("💬 Ask a Question",   callback_data="qa:topic"),
         InlineKeyboardButton("🏠 Main Menu",        callback_data="home")],
    ])

def kb_after_practice():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Try Another",   callback_data="p:next"),
         InlineKeyboardButton("💡 Show Hint",     callback_data="p:hint")],
        [InlineKeyboardButton("✅ Show Answer",   callback_data="p:answer"),
         InlineKeyboardButton("🏠 Main Menu",     callback_data="home")],
    ])

def kb_mcq(options):
    rows = [[InlineKeyboardButton(f"{letter})  {text[:50]}", callback_data=f"mcq:{letter}")]
            for letter, text in options]
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

def kb_flashcard_front(idx, total):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👁 Reveal Answer", callback_data="fc:reveal")],
        [InlineKeyboardButton("⏭ Skip", callback_data="fc:next"),
         InlineKeyboardButton("🏠 Main Menu",    callback_data="home")],
    ])

def kb_flashcard_back(idx, total):
    rows = []
    if idx < total - 1:
        rows.append([InlineKeyboardButton("⏭ Next Card",  callback_data="fc:next"),
                     InlineKeyboardButton("🔁 Restart",   callback_data="fc:restart")])
    else:
        rows.append([InlineKeyboardButton("🔁 Start Over", callback_data="fc:restart")])
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def kb_test_answer():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("A", callback_data="tq:A"),
         InlineKeyboardButton("B", callback_data="tq:B"),
         InlineKeyboardButton("C", callback_data="tq:C"),
         InlineKeyboardButton("D", callback_data="tq:D")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="home")],
    ])

def kb_next_practice():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Next Question", callback_data="p:next"),
         InlineKeyboardButton("🏠 Main Menu",     callback_data="home")],
    ])

# ── NLP-aware helpers ──────────────────────────────────────────────────────────

def parse_mcq(text):
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
    style = grade_style(grade or "Grade 6")
    context = f"{topic} in {subject}" if topic else subject
    prompt = (
        f"List exactly 6 short student questions about {context} for {grade}. "
        f"{style} Return only the questions, one per line, no numbering."
    )
    fallback = [
        f"What is {context}?",
        f"How does {context} work?",
        f"Can you give an example of {context}?",
        f"Why is {context} important?",
        f"What are common mistakes with {context}?",
        f"How can I practice {context}?",
    ]
    try:
        result = await _quick(prompt, grade or "Grade 6")
        qs = [q.strip() for q in result.get("answer", "").split("\n") if q.strip()][:6]
        return qs if len(qs) >= 3 else fallback
    except Exception:
        return fallback

def _format_nlp_header(analysis: dict, grade: str) -> str:
    """Build an emoji header based on NLP sentiment analysis."""
    sentiment = analysis.get("sentiment", {})
    confusion = sentiment.get("confusion_level", 5)
    frustration = sentiment.get("frustration_level", 5)
    emoji = grade_emoji(grade)

    if frustration >= 7:
        return f"{emoji} *Don't worry — let's figure this out together!* 💪"
    elif confusion >= 7:
        return f"{emoji} *Let me explain this more simply!* 🔍"
    else:
        return f"{emoji} *Great question! Here's the answer:*"

async def _smart_answer(question: str, grade: str) -> str:
    """NLP-enhanced answer: analyze intent → tailor the response style."""
    style = grade_style(grade or "Grade 6")
    try:
        analysis = await _nlp_analyze(question, f"{grade} student")
        intent = analysis.get("intent", "help")
        sentiment = analysis.get("sentiment", {})
        confusion = sentiment.get("confusion_level", 5)

        # Build a tailored prompt based on NLP insight
        intent_instruction = {
            "explain":  f"Explain this clearly. {style}",
            "debug":    f"Help identify and fix the issue step by step. {style}",
            "practice": f"Give a helpful worked example. {style}",
            "concept":  f"Explain the underlying concept with a relatable analogy. {style}",
            "help":     f"Provide supportive, encouraging guidance. {style}",
        }.get(intent, style)

        if confusion >= 7:
            intent_instruction += " Use extra-simple language and break it into very small steps."

        enriched_q = f"[Teaching style: {intent_instruction}]\n\nStudent question: {question}"
        result = await _quick(enriched_q, grade)
        answer = result.get("answer", "Sorry, I couldn't answer that.")

        # Add encouragement for frustrated/confused students
        if frustration >= 7 or confusion >= 7:
            answer += f"\n\n{grade_encourage(grade)}"

        return answer, analysis
    except Exception:
        result = await _quick(question, grade)
        return result.get("answer", "Sorry, couldn't answer that."), {}

async def _send_main_menu(msg, s):
    emoji = grade_emoji(s.get("grade"))
    grade_label = s.get("grade") or "Not set"
    subject_label = s.get("subject") or "Not set"
    await msg.reply_text(
        f"{emoji} *AI Tutor — Main Menu*\n\n"
        f"🎓 Grade: *{grade_label}*\n"
        f"📚 Subject: *{subject_label}*\n\n"
        f"What would you like to do? 👇",
        parse_mode="Markdown",
        reply_markup=kb_main_menu(s.get("grade")),
    )

async def _fetch_topics(msg, s, prefix):
    await msg.reply_text(f"⏳ Loading *{s['subject']}* topics...", parse_mode="Markdown")
    try:
        result = await _get_topics(s["subject"], s["grade"])
        topics = result.get("topics", [])
        if not topics:
            await msg.reply_text("No topics found for this subject.", reply_markup=kb_home())
            return False
        s["topics"] = topics
        return True
    except Exception as e:
        logger.error(f"topics error: {e}")
        await msg.reply_text("Error loading topics.", reply_markup=kb_home())
        return False

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
        "Your smart AI teacher — from Kindergarten to Grade 12! 🌟\n\n"
        "Everything works by *tapping buttons* — no typing needed.\n\n"
        "📌 First, select your *Grade* 👇",
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

    # ── GRADE ───────────────────────────────────────────────────────────────────
    if data.startswith("grade:"):
        raw = data.split(":", 1)[1]
        grade = raw if raw == "Kindergarten" else f"Grade {raw}"
        s["grade"] = grade
        s["history"] = []
        emoji = grade_emoji(grade)
        await msg.reply_text(
            f"{emoji} *{grade}* selected!\n\nNow tell me your *Age* 👇",
            parse_mode="Markdown",
            reply_markup=kb_ages(),
        )

    # ── AGE ─────────────────────────────────────────────────────────────────────
    elif data.startswith("age:"):
        s["age"] = data.split(":", 1)[1]
        await msg.reply_text(
            f"✅ Age *{s['age']}* — got it!\n\nChoose your *Subject* 👇",
            parse_mode="Markdown",
            reply_markup=kb_subjects(),
        )

    # ── SUBJECT (preset) ────────────────────────────────────────────────────────
    elif data.startswith("subject:") and data != "subject:_other":
        subject = data.split(":", 1)[1]
        s["subject"] = subject
        s["state"] = "ready"
        s["topics"] = []
        s["current_topic"] = None
        emoji = grade_emoji(s["grade"])
        await msg.reply_text(
            f"🎉 *All set!*\n\n"
            f"{emoji} Grade: *{s['grade']}*\n"
            f"📚 Subject: *{subject}*\n"
            f"🎂 Age: *{s['age']}*\n\n"
            f"Tap a button to start learning! 👇",
            parse_mode="Markdown",
            reply_markup=kb_main_menu(s["grade"]),
        )

    # ── SUBJECT (search / other) ─────────────────────────────────────────────
    elif data == "subject:_other":
        s["state"] = "ask_custom_subject"
        await msg.reply_text(
            "🔍 *Search Any Subject*\n\n"
            "Type the subject you want to learn below 👇\n\n"
            "_Examples: History, Physics, Music, Coding, Geography..._",
            parse_mode="Markdown",
        )

    # ── HOME / MAIN MENU ────────────────────────────────────────────────────────
    elif data == "home":
        if not s["subject"]:
            await msg.reply_text("👋 Let's set up first! Select your Grade:", reply_markup=kb_grades())
        else:
            await _send_main_menu(msg, s)

    # ── MENU ACTIONS ────────────────────────────────────────────────────────────
    elif data == "m:grade":
        await msg.reply_text("📊 Select your new *Grade* 👇", parse_mode="Markdown", reply_markup=kb_grades())

    elif data == "m:subject":
        await msg.reply_text("📚 Select your new *Subject* 👇", parse_mode="Markdown", reply_markup=kb_subjects())

    elif data == "m:progress":
        await _do_progress(msg, s)

    elif data == "m:flashcards":
        ok = await _fetch_topics(msg, s, "fc_topic")
        if ok:
            await msg.reply_text(
                "🃏 *Which topic for Flashcards?*\n\nTap to select 👇",
                parse_mode="Markdown",
                reply_markup=kb_topics(s["topics"], "fc_topic"),
            )

    elif data == "m:test":
        ok = await _fetch_topics(msg, s, "tt_topic")
        if ok:
            await msg.reply_text(
                "🧪 *Which topic for Test?*\n\nTap to select 👇",
                parse_mode="Markdown",
                reply_markup=kb_topics(s["topics"], "tt_topic"),
            )

    elif data == "m:topics":
        ok = await _fetch_topics(msg, s, "topic")
        if ok:
            emoji = grade_emoji(s["grade"])
            await msg.reply_text(
                f"{emoji} *{s['subject']} Topics — {s['grade']}*\n\n"
                f"Tap a topic to explore it 👇",
                parse_mode="Markdown",
                reply_markup=kb_topics(s["topics"], "topic"),
            )

    elif data == "m:explain":
        ok = await _fetch_topics(msg, s, "explain")
        if ok:
            await msg.reply_text(
                f"📖 *Which topic to explain?*\n\nTap to select 👇",
                parse_mode="Markdown",
                reply_markup=kb_topics(s["topics"], "explain"),
            )

    elif data == "m:practice":
        await _do_practice(msg, s)

    elif data == "m:videos":
        ok = await _fetch_topics(msg, s, "vtopic")
        if ok:
            await msg.reply_text(
                f"🎥 *Which topic's videos?*\n\nTap to select 👇",
                parse_mode="Markdown",
                reply_markup=kb_topics(s["topics"], "vtopic"),
            )

    elif data == "m:qa":
        await _do_qa(msg, s, s["current_topic"])

    # ── TOPIC SELECTIONS ────────────────────────────────────────────────────────
    elif data.startswith("topic:"):
        idx = int(data.split(":")[1])
        if 0 <= idx < len(s["topics"]):
            s["current_topic"] = s["topics"][idx]
            await _do_explain(msg, s)

    elif data.startswith("explain:"):
        idx = int(data.split(":")[1])
        if 0 <= idx < len(s["topics"]):
            s["current_topic"] = s["topics"][idx]
            await _do_explain(msg, s)

    elif data.startswith("vtopic:"):
        idx = int(data.split(":")[1])
        if 0 <= idx < len(s["topics"]):
            s["current_topic"] = s["topics"][idx]
            await _do_videos(msg, s)

    elif data.startswith("fc_topic:"):
        idx = int(data.split(":")[1])
        if 0 <= idx < len(s["topics"]):
            s["current_topic"] = s["topics"][idx]
            await _do_flashcards(msg, s)

    elif data.startswith("tt_topic:"):
        idx = int(data.split(":")[1])
        if 0 <= idx < len(s["topics"]):
            s["current_topic"] = s["topics"][idx]
            await _do_test(msg, s)

    # ── FLASHCARD NAVIGATION ────────────────────────────────────────────────────
    elif data == "fc:reveal":
        await _show_fc_back(msg, s)

    elif data == "fc:next":
        s["fc_idx"] = min(s["fc_idx"] + 1, len(s["flashcards"]) - 1)
        await _show_fc_front(msg, s)

    elif data == "fc:restart":
        s["fc_idx"] = 0
        await _show_fc_front(msg, s)

    # ── TEST ANSWER ─────────────────────────────────────────────────────────────
    elif data.startswith("tq:"):
        letter   = data.split(":")[1]
        questions = s["test_questions"]
        idx      = s["test_idx"]
        if idx < len(questions):
            q       = questions[idx]
            correct = q.get("correct", "").upper()
            is_correct = letter.upper() == correct
            if is_correct:
                s["test_score"] += 1
                s["practice_correct"] += 1
            total = len(questions)
            result_text = (
                f"{'✅ Correct!' if is_correct else f'❌ Wrong! Correct answer: *{correct}*'}\n\n"
                f"💡 _{q.get('explanation', '')}_"
            )
            next_idx = idx + 1
            if next_idx < total:
                s["test_idx"] = next_idx
                await msg.reply_text(result_text, parse_mode="Markdown")
                await _show_test_q(msg, s)
            else:
                score = s["test_score"]
                pct   = round(score / total * 100)
                encourage = grade_encourage(s["grade"])
                await msg.reply_text(
                    f"{result_text}\n\n"
                    f"🏆 *Test Complete!*\n━━━━━━━━━━━━━━━━\n\n"
                    f"Score: *{score}/{total}* ({pct}%)\n\n"
                    f"{'🌟 Excellent!' if pct >= 80 else '📚 Keep practicing!' if pct >= 50 else '💪 Review the topic and try again!'}\n"
                    f"{encourage}",
                    parse_mode="Markdown",
                    reply_markup=kb_home(),
                )

    # ── PRACTICE ────────────────────────────────────────────────────────────────
    elif data in ("p:topic", "p:next"):
        await _do_practice(msg, s)

    elif data == "p:hint":
        hint = s["practice_data"].get("hint") or GRADE_CONFIG.get(s["grade"] or "Grade 6", {}).get("hint_style", "Think carefully step by step! 💭")
        await msg.reply_text(
            f"💡 *Hint*\n\n{hint}",
            parse_mode="Markdown",
            reply_markup=kb_after_practice(),
        )

    elif data == "p:answer":
        answer = s["practice_data"].get("answer", "")
        if not answer:
            q = s["practice_data"].get("question", "")
            try:
                style = grade_style(s["grade"])
                enriched = f"[{style}]\nProvide a clear answer and explanation: {q}"
                res = await _quick(enriched, s["grade"])
                answer = res.get("answer", "Please try another question.")
            except Exception:
                answer = "Please try another question."
        await msg.reply_text(
            f"✅ *Answer*\n\n{answer}\n\n{grade_encourage(s['grade'])}",
            parse_mode="Markdown",
            reply_markup=kb_after_practice(),
        )

    elif data.startswith("mcq:"):
        letter = data.split(":")[1]
        correct = s["practice_data"].get("correct", "")
        if correct and letter == correct:
            await msg.reply_text(
                f"🎉 *Correct! '{letter}' is right!*\n\n{grade_encourage(s['grade'])}",
                parse_mode="Markdown",
                reply_markup=kb_next_practice(),
            )
        elif correct:
            await msg.reply_text(
                f"❌ Not quite! Correct answer: *{correct}*\n\nDon't give up — keep practicing! 💪",
                parse_mode="Markdown",
                reply_markup=kb_next_practice(),
            )
        else:
            await msg.reply_text(
                f"You selected *{letter}* — let's see the answer!",
                parse_mode="Markdown",
                reply_markup=kb_after_practice(),
            )

    # ── VIDEOS ──────────────────────────────────────────────────────────────────
    elif data == "v:topic":
        await _do_videos(msg, s)

    # ── Q&A ─────────────────────────────────────────────────────────────────────
    elif data in ("qa:topic", "qa:more"):
        await _do_qa(msg, s, s["current_topic"])

    elif data.startswith("qq:"):
        idx = int(data.split(":")[1])
        qs = s.get("qa_questions", [])
        if 0 <= idx < len(qs):
            question = qs[idx]
            await msg.reply_text(f"⏳ _{question}_", parse_mode="Markdown")
            try:
                answer, analysis = await _smart_answer(question, s["grade"] or "Grade 6")
                if len(answer) > 3800:
                    answer = answer[:3800] + "..."
                header = _format_nlp_header(analysis, s["grade"])
                await msg.reply_text(
                    f"{header}\n\n{answer}",
                    parse_mode="Markdown",
                    reply_markup=kb_after_qa(),
                )
            except Exception as e:
                logger.error(f"qa answer error: {e}")
                await msg.reply_text("Error getting answer.", reply_markup=kb_after_qa())

# ── Action functions ───────────────────────────────────────────────────────────

async def _do_explain(msg, s):
    topic = s["current_topic"]
    grade = s["grade"] or "Grade 6"
    emoji = grade_emoji(grade)
    await msg.reply_text(f"{emoji} Explaining *{topic}*...", parse_mode="Markdown")
    try:
        result = await _explain(topic, grade, s["subject"], s["history"])
        explanation = result.get("explanation", "No explanation available.")
        if len(explanation) > 3800:
            explanation = explanation[:3800] + "..."
        s["lessons_done"] = s.get("lessons_done", 0) + 1
        s["history"].append({"role": "user", "content": f"Explain {topic}"})
        s["history"].append({"role": "assistant", "content": explanation})
        s["history"] = s["history"][-10:]
        await msg.reply_text(
            f"{emoji} *{topic}*\n"
            f"━━━━━━━━━━━━━━━━\n\n"
            f"{explanation}",
            parse_mode="Markdown",
            reply_markup=kb_after_explain(),
        )
    except Exception as e:
        logger.error(f"explain error: {e}")
        await msg.reply_text("Error explaining topic.", reply_markup=kb_home())

async def _do_practice(msg, s):
    subject = s["subject"] or "Python"
    grade = s["grade"] or "Grade 6"
    emoji = grade_emoji(grade)
    await msg.reply_text(
        f"{emoji} Generating a *{grade}* level practice question...",
        parse_mode="Markdown",
    )
    try:
        result = await _practice(subject, grade)
        q_text = result.get("question", "No question generated.")
        stem, options = parse_mcq(q_text)

        if len(options) >= 2:
            correct_m = re.search(r"(?:correct answer|answer)[:\s]+([A-D])", q_text, re.IGNORECASE)
            correct = correct_m.group(1).upper() if correct_m else ""
            clean_stem = re.sub(r"\n?(?:correct answer|answer)[:\s]+[A-D].*", "", stem, flags=re.IGNORECASE).strip()
            s["practice_data"] = {"question": q_text, "answer": correct, "correct": correct, "hint": ""}
            await msg.reply_text(
                f"📝 *Practice Question — {grade}*\n"
                f"━━━━━━━━━━━━━━━━\n\n"
                f"{clean_stem}\n\n"
                f"_Tap the correct answer 👇_",
                parse_mode="Markdown",
                reply_markup=kb_mcq(options),
            )
        else:
            s["practice_data"] = {"question": q_text, "answer": "", "correct": "", "hint": ""}
            await msg.reply_text(
                f"📝 *Practice Question — {grade}*\n"
                f"━━━━━━━━━━━━━━━━\n\n"
                f"{q_text}",
                parse_mode="Markdown",
                reply_markup=kb_after_practice(),
            )
    except Exception as e:
        logger.error(f"practice error: {e}")
        await msg.reply_text("Error generating question.", reply_markup=kb_home())

async def _do_videos(msg, s):
    topic = s["current_topic"]
    subject = s["subject"] or "Python"
    grade = s["grade"] or "Grade 6"
    label = topic or subject
    await msg.reply_text(f"🎥 Finding *{grade}* videos for *{label}*...", parse_mode="Markdown")
    try:
        result = await _videos(subject, grade, topic)
        videos = result.get("videos", [])
        if not videos:
            await msg.reply_text("No videos found for this topic.", reply_markup=kb_home())
            return
        text = f"🎥 *Learning Videos — {grade}*\n📌 _{label}_\n━━━━━━━━━━━━━━━━\n\n"
        for v in videos[:5]:
            title = v.get("title", "Video")
            url = v.get("url", "")
            text += f"▶️ [{title}]({url})\n\n"
        await msg.reply_text(text, parse_mode="Markdown",
                             disable_web_page_preview=False, reply_markup=kb_home())
    except Exception as e:
        logger.error(f"videos error: {e}")
        await msg.reply_text("Error fetching videos.", reply_markup=kb_home())

async def _do_qa(msg, s, topic=None):
    subject = s["subject"] or "Python"
    grade = s["grade"] or "Grade 6"
    emoji = grade_emoji(grade)
    label = f"*{topic}*" if topic else f"*{subject}*"
    await msg.reply_text(f"⏳ Generating questions for {label}...", parse_mode="Markdown")
    questions = await _gen_qa_questions(subject, grade, topic)
    s["qa_questions"] = questions
    await msg.reply_text(
        f"{emoji} *Common Questions*\n"
        f"📌 {label} — {grade}\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"Tap a question to get the answer 👇",
        parse_mode="Markdown",
        reply_markup=kb_qa(questions),
    )

# ── Flashcard & Test AI helpers ────────────────────────────────────────────────
async def _fetch_flashcards(subject, grade, topic=None):
    from mcp_server import client as openai_client
    import json, re
    t = topic or subject
    raw = ""
    try:
        resp = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return ONLY raw JSON. No markdown, no code fences, no explanation."},
                {"role": "user", "content": (
                    f"Create 8 flashcards for '{t}' ({subject}, {grade}).\n"
                    "front = key term or question, back = clear answer (1-2 sentences).\n"
                    'Return exactly: {"flashcards":[{"front":"...","back":"..."}]}'
                )}
            ],
            temperature=0.5, max_tokens=1200,
        )
        raw = resp.choices[0].message.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0]
        raw = re.sub(r',\s*([}\]])', r'\1', raw.strip())
        return json.loads(raw).get("flashcards", [])
    except Exception as e:
        logger.error(f"flashcards fetch error: {e} | raw={raw[:200]}")
        return []

async def _fetch_test(subject, grade, topic=None):
    from mcp_server import client as openai_client
    import json, re
    t = topic or subject
    raw = ""
    try:
        resp = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return ONLY raw JSON. No markdown, no code fences, no explanation."},
                {"role": "user", "content": (
                    f"Create 5 MCQ questions about '{t}' for {grade} {subject} students.\n"
                    "Each question has 4 options A/B/C/D, correct is just the letter, short explanation.\n"
                    "Return exactly:\n"
                    '{"questions":[{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"correct":"A","explanation":"..."}]}'
                )}
            ],
            temperature=0.5, max_tokens=1800,
        )
        raw = resp.choices[0].message.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0]
        raw = re.sub(r',\s*([}\]])', r'\1', raw.strip())
        questions = json.loads(raw).get("questions", [])
        logger.info(f"Test generated: {len(questions)} questions for '{t}'")
        return questions
    except Exception as e:
        logger.error(f"test fetch error: {e} | raw={raw[:200]}")
        return []

async def _do_flashcards(msg, s):
    subject = s["subject"] or "General"
    grade   = s["grade"] or "Grade 6"
    topic   = s["current_topic"]
    label   = topic or subject
    await msg.reply_text(f"🃏 Loading flashcards for *{label}*...", parse_mode="Markdown")
    cards = await _fetch_flashcards(subject, grade, topic)
    if not cards:
        await msg.reply_text("❌ Could not generate flashcards. Try again.", reply_markup=kb_home())
        return
    s["flashcards"] = cards
    s["fc_idx"] = 0
    await _show_fc_front(msg, s)

async def _show_fc_front(msg, s):
    cards = s["flashcards"]
    idx   = s["fc_idx"]
    card  = cards[idx]
    total = len(cards)
    await msg.reply_text(
        f"🃏 *Card {idx+1}/{total}*\n━━━━━━━━━━━━━━━━\n\n"
        f"❓ *{card['front']}*\n\n_Tap 'Reveal Answer' when ready 👇_",
        parse_mode="Markdown",
        reply_markup=kb_flashcard_front(idx, total),
    )

async def _show_fc_back(msg, s):
    cards = s["flashcards"]
    idx   = s["fc_idx"]
    card  = cards[idx]
    total = len(cards)
    await msg.reply_text(
        f"🃏 *Card {idx+1}/{total}*\n━━━━━━━━━━━━━━━━\n\n"
        f"❓ {card['front']}\n\n"
        f"✅ *{card['back']}*",
        parse_mode="Markdown",
        reply_markup=kb_flashcard_back(idx, total),
    )

async def _do_test(msg, s):
    subject = s["subject"] or "General"
    grade   = s["grade"] or "Grade 6"
    topic   = s["current_topic"]
    label   = topic or subject
    await msg.reply_text(f"🧪 Generating *{grade}* test for *{label}*...", parse_mode="Markdown")
    questions = await _fetch_test(subject, grade, topic)
    if not questions:
        await msg.reply_text("❌ Could not generate test. Try again.", reply_markup=kb_home())
        return
    s["test_questions"] = questions
    s["test_idx"]   = 0
    s["test_score"] = 0
    s["practice_total"] += len(questions)
    await _show_test_q(msg, s)

async def _show_test_q(msg, s):
    questions = s["test_questions"]
    idx   = s["test_idx"]
    q     = questions[idx]
    total = len(questions)
    opts  = "\n".join(q["options"])
    await msg.reply_text(
        f"🧪 *Question {idx+1}/{total}*\n━━━━━━━━━━━━━━━━\n\n"
        f"{q['question']}\n\n{opts}\n\n_Tap your answer 👇_",
        parse_mode="Markdown",
        reply_markup=kb_test_answer(),
    )

async def _do_progress(msg, s):
    grade   = s.get("grade") or "Not set"
    subject = s.get("subject") or "Not set"
    lessons = s.get("lessons_done", 0)
    total   = s.get("practice_total", 0)
    correct = s.get("practice_correct", 0)
    pct     = round(correct / total * 100) if total else 0
    emoji   = grade_emoji(grade)
    await msg.reply_text(
        f"{emoji} *My Learning Progress*\n━━━━━━━━━━━━━━━━\n\n"
        f"🎓 Grade: *{grade}*\n"
        f"📚 Subject: *{subject}*\n\n"
        f"📖 Lessons Completed: *{lessons}*\n"
        f"📝 Test Questions: *{total}*\n"
        f"✅ Correct Answers: *{correct}* ({pct}%)\n\n"
        f"{'🔥 Great work! Keep it up!' if lessons > 0 else '👆 Start a lesson to track your progress!'}",
        parse_mode="Markdown",
        reply_markup=kb_home(),
    )

# ── Text handler — custom subject search + guard ───────────────────────────────
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    s = session(chat_id)
    text = update.message.text.strip()

    # Allow typing ONLY for custom subject search
    if s["state"] == "ask_custom_subject":
        subject = text.title()
        s["subject"] = subject
        s["state"] = "ready"
        s["topics"] = []
        s["current_topic"] = None
        emoji = grade_emoji(s["grade"])
        await update.message.reply_text(
            f"🔍 *Subject set to: {subject}*\n\n"
            f"{emoji} Grade: *{s['grade']}*  |  📚 Subject: *{subject}*\n\n"
            f"Tap a button to start learning! 👇",
            parse_mode="Markdown",
            reply_markup=kb_main_menu(s["grade"]),
        )
        return

    # Guard: redirect all other text to buttons
    if not s["subject"]:
        await update.message.reply_text(
            "👆 Please tap a button above to continue setup.",
        )
    else:
        emoji = grade_emoji(s["grade"])
        await update.message.reply_text(
            f"{emoji} Use the buttons to navigate — no typing needed! 👇",
            reply_markup=kb_main_menu(s["grade"]),
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
