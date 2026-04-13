#!/usr/bin/env python3
"""
AI Tutor Backend - Python FastAPI + MCP Integration
- REST API for Frontend (FastAPI)
- Uses MCP tools for content generation (single source of truth)
"""

import os
import re
import json
import asyncio
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
from openai import OpenAI

# RAG System for caching
try:
    from rag_system import (
        get_cached_explanation,
        cache_explanation,
        get_cached_question,
        cache_practice_question
    )
    RAG_ENABLED = True
except ImportError:
    RAG_ENABLED = False
    print("⚠️ RAG system not available. Caching disabled.")

# Import MCP tools for content generation (single source of truth)
from mcp_server import (
    get_topics as mcp_get_topics,
    explain_topic as mcp_explain_topic,
    practice_question as mcp_practice_question,
    get_educational_videos as mcp_get_videos,
)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Port
PORT = int(os.getenv("PORT", 5000))

# ─── Request Models ──────────────────────────────────────────────────────────
class GetTopicsRequest(BaseModel):
    subject: str
    grade: str

class ExplainTopicRequest(BaseModel):
    topic: str
    grade: str
    subject: Optional[str] = None

class PracticeQuestionRequest(BaseModel):
    subject: str
    grade: str

class YouTubeRequest(BaseModel):
    subject: Optional[str] = None
    grade: Optional[str] = None
    topic: Optional[str] = None
    query: Optional[str] = None

# ─── Helper Functions ────────────────────────────────────────────────────────

def get_grade_language(grade: str) -> str:
    """Return language level based on grade."""
    grade_num = int(''.join(filter(str.isdigit, grade)) or 6)

    if grade_num <= 3:
        return "Use very simple words, short sentences, and explain like you're talking to a 6-8 year old. Use lots of emojis and examples."
    elif grade_num <= 6:
        return "Use clear, age-appropriate language with some fun examples. Grades 4-6 level."
    elif grade_num <= 9:
        return "Use slightly more technical language. Grades 7-9 level. Include some advanced concepts."
    else:
        return "Use academic language with technical terminology. High school (grades 10-12) level. Detailed explanations."

# ─── Language Topics (Pre-defined for accuracy) ──────────────────────────────

LANGUAGE_TOPICS = {
    "german": ["German Alphabet", "German Vocabulary", "German Grammar", "German Verbs", "German Sentences", "German Listening", "German Writing", "German Speaking"],
    "germany": ["German Alphabet", "German Vocabulary", "German Grammar", "German Verbs", "German Sentences", "German Listening", "German Writing", "German Speaking"],
    "spanish": ["Spanish Alphabet", "Spanish Vocabulary", "Spanish Grammar", "Spanish Verbs", "Spanish Sentences", "Spanish Listening", "Spanish Writing", "Spanish Speaking"],
    "spanish language": ["Spanish Alphabet", "Spanish Vocabulary", "Spanish Grammar", "Spanish Verbs", "Spanish Sentences", "Spanish Listening", "Spanish Writing", "Spanish Speaking"],
    "french": ["French Alphabet", "French Vocabulary", "French Grammar", "French Verbs", "French Sentences", "French Listening", "French Writing", "French Speaking"],
    "russian": ["Russian Alphabet", "Russian Vocabulary", "Russian Grammar", "Russian Verbs", "Russian Sentences", "Russian Listening", "Russian Writing", "Russian Speaking"],
    "chinese": ["Chinese Characters", "Chinese Vocabulary", "Chinese Grammar", "Chinese Tones", "Chinese Sentences", "Chinese Listening", "Chinese Writing", "Chinese Speaking"],
    "japanese": ["Japanese Hiragana", "Japanese Vocabulary", "Japanese Grammar", "Japanese Kanji", "Japanese Sentences", "Japanese Listening", "Japanese Writing", "Japanese Speaking"],
    "korean": ["Korean Alphabet", "Korean Vocabulary", "Korean Grammar", "Korean Verbs", "Korean Sentences", "Korean Listening", "Korean Writing", "Korean Speaking"],
    "italian": ["Italian Alphabet", "Italian Vocabulary", "Italian Grammar", "Italian Verbs", "Italian Sentences", "Italian Listening", "Italian Writing", "Italian Speaking"],
    "portuguese": ["Portuguese Alphabet", "Portuguese Vocabulary", "Portuguese Grammar", "Portuguese Verbs", "Portuguese Sentences", "Portuguese Listening", "Portuguese Writing", "Portuguese Speaking"],
    "arabic": ["Arabic Alphabet", "Arabic Vocabulary", "Arabic Grammar", "Arabic Verbs", "Arabic Sentences", "Arabic Listening", "Arabic Writing", "Arabic Speaking"],
}

# ─── GRADE_TOPICS (from constants.js) ────────────────────────────────────────

GRADE_TOPICS = {
    "mathematics": {
        "Grade 1": ["Counting", "Numbers 1-10", "Addition Basics", "Subtraction Basics", "Shapes"],
        "Grade 2": ["Skip Counting", "Addition 2-Digit", "Subtraction 2-Digit", "Word Problems", "Measurement"],
        "Grade 3": ["Multiplication Basics", "Division Basics", "Fractions", "Time & Clocks", "Data & Graphs"],
        "Grade 4": ["Multi-Digit Multiplication", "Division with Remainders", "Fractions Comparison", "Decimals", "Area & Perimeter"],
        "Grade 5": ["Fractions Operations", "Decimals Operations", "Percentages", "Ratios", "Volume"],
        "Grade 6": ["Integers", "Expressions", "Equations", "Ratios & Rates", "Probability"],
        "Grade 7": ["Linear Equations", "Systems of Equations", "Polynomials", "Factoring", "Exponents"],
        "Grade 8": ["Quadratic Equations", "Graphing Functions", "Pythagorean Theorem", "Radicals", "Exponential Growth"],
        "Grade 9": ["Functions", "Transformations", "Sequences", "Complex Numbers", "Matrices"],
        "Grade 10": ["Trigonometry Basics", "Sine & Cosine", "Logarithms", "Conic Sections", "Combinatorics"],
        "Grade 11": ["Advanced Trigonometry", "Calculus Intro", "Limits", "Derivatives", "Probability Distributions"],
        "Grade 12": ["Calculus", "Integrals", "Series", "Differential Equations", "Linear Algebra"],
    },
    "science": {
        "Grade 1": ["Living Things", "Plants", "Animals", "Weather", "Five Senses"],
        "Grade 2": ["Habitats", "Life Cycles", "Seasons", "Water Cycle", "Human Body Basics"],
        "Grade 3": ["Ecosystems", "Food Chains", "Rocks & Soil", "Weather Patterns", "Simple Machines"],
        "Grade 4": ["States of Matter", "Forces & Motion", "Earth's Layers", "Solar System", "Energy Sources"],
        "Grade 5": ["Elements & Compounds", "Chemical Reactions", "Waves", "Weather Systems", "Cells"],
        "Grade 6": ["Atoms & Molecules", "Periodic Table", "Physics Basics", "Earth Science", "Genetics Intro"],
        "Grade 7": ["Chemical Bonding", "Photosynthesis", "Respiration", "Reproduction", "Evolution Basics"],
        "Grade 8": ["Atomic Structure", "Chemical Equations", "Ecosystems & Biomes", "Plate Tectonics", "Electricity"],
        "Grade 9": ["Quantum Mechanics Intro", "Thermodynamics", "Organic Chemistry", "Genetics", "Astronomy"],
        "Grade 10": ["Chemical Kinetics", "Stoichiometry", "Advanced Genetics", "Ecology", "Nuclear Physics"],
        "Grade 11": ["Biochemistry", "Microbiology", "Immunology", "Cosmology", "Relativity"],
        "Grade 12": ["Molecular Biology", "Neuroscience", "Astrophysics", "Quantum Chemistry", "Systems Biology"],
    },
    "english": {
        "Grade 1": ["Alphabet", "Phonics", "Sight Words", "Simple Stories", "Letters & Sounds"],
        "Grade 2": ["Word Families", "Rhyming", "Simple Sentences", "Punctuation", "Story Elements"],
        "Grade 3": ["Nouns", "Verbs", "Adjectives", "Reading Comprehension", "Creative Writing"],
        "Grade 4": ["Pronouns", "Tenses", "Paragraphs", "Main Idea & Details", "Book Reports"],
        "Grade 5": ["Sentence Structure", "Punctuation Rules", "Figurative Language", "Summarizing", "Poetry"],
        "Grade 6": ["Parts of Speech", "Complex Sentences", "Writing Styles", "Literature Analysis", "Grammar Rules"],
        "Grade 7": ["Sentence Diagramming", "Literary Devices", "Essay Writing", "Vocabulary", "Debate Skills"],
        "Grade 8": ["Tone & Mood", "Character Analysis", "Plot Development", "Symbolism", "Research Writing"],
        "Grade 9": ["Shakespearian Literature", "Rhetoric", "Analytical Writing", "Modern Novels", "Persuasion"],
        "Grade 10": ["American Literature", "Thematic Analysis", "Critical Essays", "Poetry Interpretation", "Journalism"],
        "Grade 11": ["British Literature", "Modernism", "Advanced Grammar", "Philosophical Texts", "Media Analysis"],
        "Grade 12": ["World Literature", "Literary Theory", "Sophistry", "Academic Writing", "Communication Arts"],
    },
    "history": {
        "Grade 1": ["Community Helpers", "Family History", "Holidays", "Past & Present", "Culture"],
        "Grade 2": ["Native Americans", "Pilgrims", "Thanksgiving", "Presidents", "Famous People"],
        "Grade 3": ["Colonial America", "American Revolution", "Native American Tribes", "Exploration", "Continents"],
        "Grade 4": ["State History", "Geography", "Gold Rush", "Civil War", "Westward Expansion"],
        "Grade 5": ["American History", "Indigenous Peoples", "Founding Fathers", "Industrial Revolution", "Slavery"],
        "Grade 6": ["Ancient Civilizations", "Greece & Rome", "Medieval Times", "Renaissance", "Exploration Age"],
        "Grade 7": ["American Independence", "Constitution", "Early America", "Industrial Growth", "Civil Rights"],
        "Grade 8": ["American Civil War", "Reconstruction", "Manifest Destiny", "Great Depression", "World War I"],
        "Grade 9": ["World War II", "Cold War", "Civil Rights Movement", "Asian History", "African History"],
        "Grade 10": ["European History", "Middle East Conflicts", "Modern Nations", "Colonialism", "Nationalism"],
        "Grade 11": ["20th Century History", "Global Conflicts", "Political Systems", "Economic Systems", "Cultural Movements"],
        "Grade 12": ["World Civilization", "International Relations", "Modern Geopolitics", "Historical Analysis", "Philosophy of History"],
    },
    "cs": {
        "Grade 1": ["Computers Basics", "Keyboard & Mouse", "Digital Citizenship", "Internet Safety", "Typing"],
        "Grade 2": ["Programs", "Algorithms", "Logic Puzzles", "Digital Tools", "Online Learning"],
        "Grade 3": ["Coding Basics", "Commands", "Loops", "Conditionals", "Problem Solving"],
        "Grade 4": ["Variables", "Functions", "Data Types", "Debugging", "Sequences & Patterns"],
        "Grade 5": ["Control Flow", "Lists", "Loops & Repetition", "Error Handling", "Algorithm Design"],
        "Grade 6": ["Variables & Data", "Functions", "Lists & Arrays", "String Manipulation", "File Handling"],
        "Grade 7": ["Functions", "Recursion Basics", "Data Structures", "Object Basics", "Design Patterns"],
        "Grade 8": ["Lists & Arrays", "Sorting Algorithms", "Searching", "Hash Tables", "Graphs Intro"],
        "Grade 9": ["Intro to OOP", "Classes & Objects", "Inheritance", "Polymorphism", "Design Principles"],
        "Grade 10": ["Recursion", "Sorting & Searching", "Data Structures", "Algorithms Complexity", "Trees"],
        "Grade 11": ["Advanced Data Structures", "Algorithm Analysis", "Database Basics", "Networks", "Security Basics"],
        "Grade 12": ["Data Structures", "Algorithm Optimization", "Compiler Theory", "System Design", "Distributed Systems"],
    },
    "ai": {
        "Grade 1": ["What is AI?", "Robots", "Smart Devices", "AI in Daily Life", "Future Technology"],
        "Grade 2": ["Computers Learning", "AI Helpers", "Voice Assistants", "Pattern Recognition", "Automation"],
        "Grade 3": ["Machine Learning Basics", "Training Data", "AI Games", "Decision Making", "AI Tools"],
        "Grade 4": ["Computers & Learning", "Training Models", "Recognition", "Prediction", "AI Ethics"],
        "Grade 5": ["Pattern Recognition", "Classification", "Regression", "AI Applications", "Data Importance"],
        "Grade 6": ["Machine Learning Basics", "Training Data", "Features", "Model Types", "Evaluation Metrics"],
        "Grade 7": ["Neural Networks", "Activation Functions", "Backpropagation", "Loss Functions", "Optimization"],
        "Grade 8": ["AI Training & Data", "Overfitting", "Regularization", "Cross Validation", "Hyperparameters"],
        "Grade 9": ["Supervised Learning", "Decision Trees", "Support Vector Machines", "Ensemble Methods", "Clustering"],
        "Grade 10": ["Unsupervised Learning", "K-Means", "Hierarchical Clustering", "Dimensionality Reduction", "Anomaly Detection"],
        "Grade 11": ["NLP & Computer Vision", "Text Processing", "Image Recognition", "Deep Learning", "Transformers"],
        "Grade 12": ["AI Ethics & Deep Learning", "Reinforcement Learning", "Generative Models", "AI Safety", "Advanced NLP"],
    },
    "webdev": {
        "Grade 1": ["What is Internet?", "Websites", "Web Browsers", "Online Safety", "Digital Devices"],
        "Grade 2": ["HTML Basics", "Web Pages", "Links", "Text Formatting", "Web Colors"],
        "Grade 3": ["HTML Tags", "Paragraphs & Headings", "Images", "Lists", "Attributes"],
        "Grade 4": ["HTML Basics", "More HTML", "Divs & Sections", "Forms", "Input Elements"],
        "Grade 5": ["CSS Styling", "Colors & Fonts", "Borders & Margins", "Classes & IDs", "Box Model"],
        "Grade 6": ["CSS Styling", "CSS Layouts", "Flexbox Basics", "Grid Basics", "Positioning"],
        "Grade 7": ["CSS Layouts", "Responsive Design", "Media Queries", "Mobile First", "Grid Advanced"],
        "Grade 8": ["JavaScript Basics", "Variables", "Functions", "Events", "DOM Manipulation"],
        "Grade 9": ["JavaScript & DOM", "Event Listeners", "Data Types", "Loops & Conditions", "Array Methods"],
        "Grade 10": ["Responsive Design", "Bootstrap", "CSS Framework", "Version Control", "APIs & Fetch"],
        "Grade 11": ["APIs & Fetch", "Promises", "Async/Await", "JSON", "REST APIs"],
        "Grade 12": ["React & Frameworks", "Components", "State Management", "Hooks", "Full Stack Development"],
    },
    "blocks": {
        "Grade 1": ["Scratch Basics", "Blocks Overview", "Sprites", "Backdrops", "Sound Blocks"],
        "Grade 2": ["Events & Actions", "Click Events", "Key Press", "Broadcast", "Message Passing"],
        "Grade 3": ["Loops in Blocks", "Repeat Block", "Forever Loop", "Until Loop", "Loop Control"],
        "Grade 4": ["Conditionals in Blocks", "If Block", "If-Else", "Comparison", "Logic Gates"],
        "Grade 5": ["Variables in Blocks", "Create Variable", "Set Variable", "Variable Operations", "Scope"],
        "Grade 6": ["Conditionals in Blocks", "Multiple Conditions", "Nested If", "Boolean Logic", "Decision Trees"],
        "Grade 7": ["Variables in Blocks", "Lists", "List Operations", "Iteration", "Data Structures"],
        "Grade 8": ["Functions & My Blocks", "Define Function", "Parameters", "Return Values", "Recursion"],
        "Grade 9": ["Clone Blocks", "Object Oriented", "Inheritance", "Polymorphism", "Game Design"],
        "Grade 10": ["Custom Blocks", "Advanced Logic", "State Management", "Game Development", "Animation"],
        "Grade 11": ["Performance Optimization", "Algorithm Implementation", "Debugging Blocks", "Complex Games", "Educational Games"],
        "Grade 12": ["Advanced Game Design", "Multiplayer Logic", "Physics Simulation", "AI in Games", "Game Publishing"],
    },
}

# ─── API Endpoints ───────────────────────────────────────────────────────────

@app.post("/api/mcp/get-topics")
async def get_topics(request: GetTopicsRequest):
    """Get topics using MCP tool (single source of truth)."""
    print(f"📚 Getting topics for {request.subject} ({request.grade})...")
    return mcp_get_topics(request.subject, request.grade)

@app.post("/api/mcp/explain-topic")
async def explain_topic(request: ExplainTopicRequest):
    """Explain a topic using MCP tool (single source of truth)."""
    try:
        subject = request.subject or "this topic"

        # Check cache first
        if RAG_ENABLED:
            cached = get_cached_explanation(request.topic, request.grade, subject)
            if cached:
                return {
                    "topic": request.topic,
                    "grade": request.grade,
                    "subject": subject,
                    "sections": cached['sections'],
                    "cached": True
                }

        # Use MCP tool
        result = mcp_explain_topic(request.topic, request.grade, subject)

        # Cache the result
        if RAG_ENABLED and 'sections' in result:
            cache_explanation(request.topic, request.grade, subject, result.get('sections', {}))

        return result
    except Exception as e:
        print(f"❌ Error explaining topic: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mcp/practice-question")
async def practice_question(request: PracticeQuestionRequest):
    """Generate a practice question using MCP tool (single source of truth)."""
    try:
        # Check cache first
        if RAG_ENABLED:
            cached_q = get_cached_question(request.subject, request.grade)
            if cached_q:
                print(f"✅ Question Cache HIT: {request.subject} ({request.grade})")
                return {
                    "subject": request.subject,
                    "grade": request.grade,
                    "question": cached_q,
                    "cached": True
                }

        # Use MCP tool
        result = mcp_practice_question(request.subject, request.grade)

        # Cache the result
        if RAG_ENABLED and 'question' in result:
            cache_practice_question(request.subject, request.grade, result.get('question', ''))

        return result
    except Exception as e:
        print(f"❌ Error generating question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/youtube")
async def youtube_search(request: YouTubeRequest):
    """Search for YouTube videos using MCP tool (single source of truth)."""
    topic = request.topic or request.query or request.subject
    print(f"🎬 Searching videos for {topic} ({request.grade})...")
    return mcp_get_videos(request.subject, request.grade, topic)

# ─── Serve Frontend ──────────────────────────────────────────────────────────

# Build path to frontend dist folder
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

# Mount static files if they exist
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

@app.get("/")
async def root():
    """Serve index.html for root path."""
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Frontend not built. Run: cd frontend && npm run build"}

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve frontend files or index.html for client-side routing."""
    # Don't serve API routes through this handler
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404)

    file_path = FRONTEND_DIST / full_path

    # If file exists, serve it
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)

    # Otherwise serve index.html (for client-side routing)
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    raise HTTPException(status_code=404)

# ─── MCP Server Tools ────────────────────────────────────────────────────────

# Tools for MCP (Model Context Protocol) - Claude can call these
MCP_TOOLS = [
    {
        "name": "get-topics",
        "description": "Get learning topics for a subject at a specific grade level",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Subject name (e.g., mathematics, spanish, cooking)"},
                "grade": {"type": "string", "description": "Grade level (e.g., Grade 6, Grade 12)"}
            },
            "required": ["subject", "grade"]
        }
    },
    {
        "name": "explain-topic",
        "description": "Get a detailed explanation of a topic with structured sections",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic to explain"},
                "grade": {"type": "string", "description": "Grade level"},
                "subject": {"type": "string", "description": "Subject (optional)"}
            },
            "required": ["topic", "grade"]
        }
    },
    {
        "name": "practice-question",
        "description": "Generate a practice question for a subject",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Subject name"},
                "grade": {"type": "string", "description": "Grade level"}
            },
            "required": ["subject", "grade"]
        }
    },
    {
        "name": "youtube-search",
        "description": "Search for YouTube videos on a topic",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "grade": {"type": "string", "description": "Grade level"},
                "subject": {"type": "string", "description": "Subject"}
            },
            "required": ["query", "grade", "subject"]
        }
    }
]

@app.get("/mcp/tools")
async def mcp_tools():
    """Get list of MCP tools available"""
    return {"tools": MCP_TOOLS}

@app.post("/mcp/call")
async def mcp_call(tool_name: str, input_data: dict):
    """Call an MCP tool with given inputs"""
    try:
        if tool_name == "get-topics":
            req = GetTopicsRequest(**input_data)
            return await get_topics(req)
        elif tool_name == "explain-topic":
            req = ExplainTopicRequest(**input_data)
            return await explain_topic(req)
        elif tool_name == "practice-question":
            req = PracticeQuestionRequest(**input_data)
            return await practice_question(req)
        elif tool_name == "youtube-search":
            req = YouTubeRequest(**input_data)
            return await youtube_search(req)
        else:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ─── Run Server ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    import sys
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
    print(f"[*] AI Tutor Backend starting on http://localhost:{PORT}")
    print(f"[*] Serving frontend from: {FRONTEND_DIST}")
    print(f"[*] MCP Tools available at: http://localhost:{PORT}/mcp/tools")
    print(f"[*] Call MCP tools at: http://localhost:{PORT}/mcp/call")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
