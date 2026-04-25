#!/usr/bin/env python3
"""
AI Tutor Backend + MCP Server
- REST API for Frontend
- MCP Tools for Claude
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables FIRST before importing NLP engine
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from mcp_server import get_topics, explain_topic, explain_topic_stream, practice_question, get_educational_videos, quick_answer, TOOLS
from nlp_engine import nlp_engine

# Import database with explicit error handling
try:
    from database import db
    DB_IMPORT_SUCCESS = True
    DB_IMPORT_ERROR = None
except Exception as e:
    DB_IMPORT_SUCCESS = False
    DB_IMPORT_ERROR = str(e)
    print(f"[✗] CRITICAL: Failed to import database module: {e}")
    # Create a dummy db object to prevent crashes
    class DummyDB:
        db_path = "ERROR: DATABASE IMPORT FAILED"
    db = DummyDB()

# Fix Unicode encoding on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

app = FastAPI()

# Startup event - verify database is initialized
@app.on_event("startup")
async def startup_event():
    import time
    print("\n" + "="*60)
    print(f"[✓ STARTUP] AI Tutor Backend v2.0 - {time.time()}")
    print("="*60)

    if not DB_IMPORT_SUCCESS:
        print(f"[✗] DATABASE IMPORT FAILED: {DB_IMPORT_ERROR}")
        print("[✗] The following endpoints may not work:")
        print("[✗]   - /api/chat-history")
        print("[✗]   - /api/check-usage")
        print("[✗]   - /api/increment-usage")
        print("[✗]   - /api/save-chat")
    else:
        print(f"[✓] Database Path: {db.db_path}")
        print("[✓] Chat History: /api/chat-history (POST)")
        print("[✓] Check Usage: /api/check-usage (POST)")
        print("[✓] Increment Usage: /api/increment-usage (POST)")
        print("[✓] Save Chat: /api/save-chat (POST)")
        print("[✓] Features: Chat History, Usage Counter, Auto-Cleanup")

    print("="*60 + "\n")

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PORT = int(os.getenv("PORT", 5000))

# ═══════════════════════════════════════════════════════════════════════════
# REQUEST MODELS
# ═══════════════════════════════════════════════════════════════════════════

class GetTopicsRequest(BaseModel):
    subject: str
    grade: str

class ExplainTopicRequest(BaseModel):
    topic: str
    grade: str
    subject: str
    history: list = []

class PracticeQuestionRequest(BaseModel):
    subject: str
    grade: str

class MCPCallRequest(BaseModel):
    tool_name: str
    params: dict

# ═══════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    """Health check endpoint that lists all registered routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else ["GET"]
            })

    return {
        "status": "healthy" if DB_IMPORT_SUCCESS else "degraded",
        "database_import": "success" if DB_IMPORT_SUCCESS else "failed",
        "database_error": DB_IMPORT_ERROR,
        "database": db is not None,
        "db_path": db.db_path if db else "not initialized",
        "total_routes": len(routes),
        "routes": sorted(routes, key=lambda x: x['path'])
    }

# ═══════════════════════════════════════════════════════════════════════════
# API ENDPOINTS - Using MCP Server Functions
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/mcp/get-topics")
async def api_get_topics(request: GetTopicsRequest):
    """Get topics for a subject (standard or custom)"""
    return get_topics(request.subject, request.grade)

@app.post("/api/mcp/explain-topic")
async def api_explain_topic(request: ExplainTopicRequest):
    """Explain a topic"""
    result = explain_topic(request.topic, request.grade, request.subject, history=request.history or [])

    # Log what we're returning
    import json
    return_obj = {
        "topic": result.get("topic"),
        "grade": result.get("grade"),
        "subject": result.get("subject"),
        "explanation": result.get("explanation"),
        "sections": result.get("sections") or {},
        "gradeLevel": result.get("gradeLevel")
    }
    print(f"[RETURN] Keys being returned: {list(return_obj.keys())}")
    print(f"[RETURN] Sections type: {type(return_obj['sections'])}, len: {len(return_obj.get('sections', {}))}")
    return return_obj

@app.post("/api/mcp/explain-topic-stream")
async def api_explain_topic_stream(request: ExplainTopicRequest):
    """Stream explanation token by token — text appears as it's generated"""
    import json

    def generate():
        try:
            for token in explain_topic_stream(
                request.topic, request.grade, request.subject,
                history=request.history or []
            ):
                yield f"data: {json.dumps({'text': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@app.post("/api/mcp/practice-question")
async def api_practice_question(request: PracticeQuestionRequest):
    """Generate a practice question"""
    return practice_question(request.subject, request.grade)

# ═══════════════════════════════════════════════════════════════════════════
# YOUTUBE VIDEO SEARCH
# ═══════════════════════════════════════════════════════════════════════════

class YouTubeRequest(BaseModel):
    subject: Optional[str] = None
    grade: Optional[str] = None
    topic: Optional[str] = None

class SaveChatRequest(BaseModel):
    student_id: str
    topic: str
    grade_level: str
    subject: str
    request_data: dict
    response_preview: str
    response_content: str = None

class ChatHistoryRequest(BaseModel):
    student_id: str

class UsageCheckRequest(BaseModel):
    student_id: str
    lesson_type: str

class UsageIncrementRequest(BaseModel):
    student_id: str
    lesson_type: str
    query: Optional[str] = None

class QuickAnswerRequest(BaseModel):
    question: str
    grade: Optional[str] = "Grade 6"

@app.post("/api/youtube")
async def search_youtube(request: YouTubeRequest):
    """Search YouTube for educational videos using MCP tool"""
    topic = request.topic or request.query or request.subject
    print(f"🎬 Searching videos for {topic} ({request.grade})...")
    return get_educational_videos(request.subject, request.grade, topic)

@app.post("/api/quick-answer")
async def get_quick_answer(request: QuickAnswerRequest):
    """Get quick answer to any question (2-4 sentences) with current information"""
    print(f"❓ Answering question: {request.question[:50]}...")
    return quick_answer(request.question, request.grade)

# ═══════════════════════════════════════════════════════════════════════════
# MCP ENDPOINTS - For Claude to call
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/mcp/tools")
async def mcp_tools():
    """Get available MCP tools"""
    return {"tools": TOOLS}

@app.post("/mcp/call")
async def mcp_call(request: MCPCallRequest):
    """Call an MCP tool directly"""
    tool_name = request.tool_name
    params = request.params

    if tool_name == "get-topics":
        return get_topics(params["subject"], params["grade"])
    elif tool_name == "explain-topic":
        return explain_topic(params["topic"], params["grade"], params["subject"])
    elif tool_name == "practice-question":
        return practice_question(params["subject"], params["grade"])
    elif tool_name == "get-videos":
        return get_educational_videos(params["subject"], params["grade"])
    else:
        return {"error": f"Unknown tool: {tool_name}"}

# ═══════════════════════════════════════════════════════════════════════════
# CHAT HISTORY & USAGE TRACKING
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/save-chat")
async def save_chat(request: SaveChatRequest):
    """Save a chat to history"""
    try:
        chat_id = db.save_chat(
            request.student_id,
            request.topic,
            request.grade_level,
            request.subject,
            request.request_data,
            request.response_preview,
            request.response_content or request.response_preview
        )
        return {
            "success": True,
            "chat_id": chat_id,
            "message": "Chat saved to history"
        }
    except Exception as e:
        print(f"[ERROR] Failed to save chat: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/chat-history")
async def get_chat_history(request: ChatHistoryRequest):
    """Get last 7 chats for a student"""
    try:
        chats = db.get_last_7_chats(request.student_id)
        return {
            "student_id": request.student_id,
            "chats": chats,
            "count": len(chats),
            "success": True
        }
    except Exception as e:
        print(f"[ERROR] Failed to get chat history: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/check-usage")
async def check_usage(request: UsageCheckRequest):
    """Check daily usage for a lesson type"""
    try:
        result = db.check_usage(request.student_id, request.lesson_type)
        return result
    except Exception as e:
        print(f"[ERROR] Failed to check usage: {e}")
        return {"usage_count": 0, "limit": 50, "remaining": 50, "exceeded": False}

@app.post("/api/increment-usage")
async def increment_usage(request: UsageIncrementRequest):
    """Increment usage count for today"""
    try:
        result = db.increment_usage(request.student_id, request.lesson_type)
        return result
    except Exception as e:
        print(f"[ERROR] Failed to increment usage: {e}")
        return {"usage_count": 0, "limit": 50, "remaining": 50, "exceeded": False}

# ═══════════════════════════════════════════════════════════════════════════
# NLP ANALYSIS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

class NLPAnalysisRequest(BaseModel):
    question: str
    context: str = ""
    grade_level: str = "6"

class NLPIntentRequest(BaseModel):
    text: str

class NLPSentimentRequest(BaseModel):
    text: str

class NLPTopicRequest(BaseModel):
    text: str

@app.post("/api/nlp/analyze")
async def analyze_question(request: NLPAnalysisRequest):
    """Comprehensive NLP analysis of student question"""
    try:
        analysis = nlp_engine.analyze_question(request.question, request.context)
        return {"success": True, "analysis": analysis}
    except Exception as e:
        print(f"[ERROR] NLP Analysis failed: {e}")
        return {"success": False, "error": str(e), "analysis": None}

@app.post("/api/nlp/intent")
async def detect_intent(request: NLPIntentRequest):
    """Detect intent from text (explain, debug, practice, etc)"""
    try:
        intent = nlp_engine.detect_intent(request.text)
        return {"success": True, "intent": intent}
    except Exception as e:
        print(f"[ERROR] Intent detection failed: {e}")
        return {"success": False, "error": str(e), "intent": None}

@app.post("/api/nlp/sentiment")
async def analyze_sentiment(request: NLPSentimentRequest):
    """Analyze emotional state (frustration, confusion, confidence)"""
    try:
        sentiment = nlp_engine.analyze_sentiment(request.text)
        return {"success": True, "sentiment": sentiment}
    except Exception as e:
        print(f"[ERROR] Sentiment analysis failed: {e}")
        return {"success": False, "error": str(e), "sentiment": None}

@app.post("/api/nlp/topics")
async def extract_topics(request: NLPTopicRequest):
    """Extract programming topics from text"""
    try:
        topics = nlp_engine.extract_topics(request.text)
        return {"success": True, "topics": topics}
    except Exception as e:
        print(f"[ERROR] Topic extraction failed: {e}")
        return {"success": False, "error": str(e), "topics": []}

@app.post("/api/nlp/classify")
async def classify_question(request: NLPAnalysisRequest):
    """Classify question and get teaching strategy"""
    try:
        strategy = nlp_engine.classify_question_type(request.question)
        return {"success": True, "strategy": strategy}
    except Exception as e:
        print(f"[ERROR] Question classification failed: {e}")
        return {"success": False, "error": str(e), "strategy": None}

@app.post("/api/nlp/adaptive-response")
async def generate_adaptive_response(request: NLPAnalysisRequest):
    """Generate adaptive response with NLP insights"""
    try:
        # In real usage, base_response would come from the AI
        # For now, we'll just return the analysis
        adaptive = nlp_engine.generate_adaptive_response(
            request.question,
            "Base response from AI model",
            request.grade_level
        )
        return {"success": True, "adaptive": adaptive}
    except Exception as e:
        print(f"[ERROR] Adaptive response generation failed: {e}")
        return {"success": False, "error": str(e), "adaptive": None}

# ═══════════════════════════════════════════════════════════════════════════
# SERVE FRONTEND
# ═══════════════════════════════════════════════════════════════════════════

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

@app.get("/")
async def root():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Frontend not built"}

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    # Only serve static files and fallback to index.html
    # API and MCP routes are handled by specific endpoints above

    # Don't serve /api/* or /mcp/* paths - let FastAPI handle them
    if full_path.startswith("api/") or full_path.startswith("mcp/"):
        return {"error": "Not found"}

    file_path = FRONTEND_DIST / full_path
    if file_path.exists():
        return FileResponse(file_path)

    # Fallback to index.html for client-side routing
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    return {"error": "Not found"}


# ═══════════════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print(f"[*] AI Tutor Backend running on http://localhost:{PORT}")
    print("[*] Features: Chat History, Usage Counter, Auto-Cleanup")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
