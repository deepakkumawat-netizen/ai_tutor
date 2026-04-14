#!/usr/bin/env python3
"""
AI Tutor Backend + MCP Server
- REST API for Frontend
- MCP Tools for Claude
"""

import os
import sys
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from mcp_server import get_topics, explain_topic, practice_question, get_educational_videos, quick_answer, TOOLS
from database import db

# Fix Unicode encoding on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

app = FastAPI()

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

class PracticeQuestionRequest(BaseModel):
    subject: str
    grade: str

class MCPCallRequest(BaseModel):
    tool_name: str
    params: dict

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
    result = explain_topic(request.topic, request.grade, request.subject)

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

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    # Block API routes from being caught by the catch-all (they should be handled by @app.post above)
    if full_path.startswith("api/") or full_path.startswith("mcp/"):
        return {"error": "Not found"}

    file_path = FRONTEND_DIST / full_path
    if file_path.exists():
        return FileResponse(file_path)

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
