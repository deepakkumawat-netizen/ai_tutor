"""Multi-agent crew integration for AI-Tutor"""
from crew import generate_personalized_tutoring

def handle_tutoring_crew(topic: str, grade_level: str, learning_style: str = "visual") -> dict:
    """Handle multi-agent crew request for personalized tutoring"""
    try:
        result = generate_personalized_tutoring(topic, grade_level, learning_style)
        return {
            "status": "success",
            "tutoring_content": result["tutoring_content"],
            "assessment": result["assessment"],
            "learning_style": learning_style,
            "agents_used": ["tutor", "assessor"]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "agents_used": []
        }
