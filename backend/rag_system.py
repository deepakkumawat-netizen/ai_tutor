"""
Simple JSON-based Cache for AI Tutor - NO DEPENDENCIES!
Just files on disk. Fast, simple, reliable.
"""

import json
import os
from typing import Optional, Dict
from pathlib import Path

# Cache directory
CACHE_DIR = Path("./cache")
CACHE_DIR.mkdir(exist_ok=True)

EXPLANATIONS_FILE = CACHE_DIR / "explanations.json"
QUESTIONS_FILE = CACHE_DIR / "questions.json"

# Load existing cache
def _load_json_file(filepath: Path) -> Dict:
    """Load JSON file or return empty dict"""
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def _save_json_file(filepath: Path, data: Dict) -> None:
    """Save JSON file"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Cache write error: {str(e)}")

def create_cache_key(topic: str, grade: str, subject: str) -> str:
    """Create unique cache key"""
    return f"{subject}|{topic}|{grade}".lower()

def get_cached_explanation(topic: str, grade: str, subject: str) -> Optional[Dict]:
    """Get cached explanation if exists"""
    cache = _load_json_file(EXPLANATIONS_FILE)
    key = create_cache_key(topic, grade, subject)

    if key in cache:
        print(f"✅ Cache HIT: {topic} ({grade})")
        return {
            "topic": topic,
            "grade": grade,
            "subject": subject,
            "sections": cache[key],
            "cached": True
        }

    print(f"🔄 Cache MISS: {topic} ({grade})")
    return None

def cache_explanation(topic: str, grade: str, subject: str, sections: Dict) -> None:
    """Cache explanation"""
    cache = _load_json_file(EXPLANATIONS_FILE)
    key = create_cache_key(topic, grade, subject)
    cache[key] = sections
    _save_json_file(EXPLANATIONS_FILE, cache)
    print(f"💾 Cached: {topic} ({grade})")

def get_cached_question(subject: str, grade: str) -> Optional[str]:
    """Get cached question if exists"""
    cache = _load_json_file(QUESTIONS_FILE)
    key = f"{subject}|{grade}".lower()

    if key in cache:
        print(f"✅ Question Cache HIT: {subject} ({grade})")
        return cache[key]

    print(f"🔄 Question Cache MISS: {subject} ({grade})")
    return None

def cache_practice_question(subject: str, grade: str, question: str) -> None:
    """Cache practice question"""
    cache = _load_json_file(QUESTIONS_FILE)
    key = f"{subject}|{grade}".lower()
    cache[key] = question
    _save_json_file(QUESTIONS_FILE, cache)
    print(f"💾 Question Cached: {subject} ({grade})")

def clear_cache() -> None:
    """Clear all cache"""
    try:
        EXPLANATIONS_FILE.unlink(missing_ok=True)
        QUESTIONS_FILE.unlink(missing_ok=True)
        print("✅ Cache cleared")
    except Exception as e:
        print(f"⚠️ Error clearing cache: {str(e)}")

def get_cache_stats() -> Dict:
    """Get cache statistics"""
    exp_cache = _load_json_file(EXPLANATIONS_FILE)
    q_cache = _load_json_file(QUESTIONS_FILE)

    return {
        "explanations_cached": len(exp_cache),
        "questions_cached": len(q_cache),
        "total_items": len(exp_cache) + len(q_cache)
    }
