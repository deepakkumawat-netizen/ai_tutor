"""Multi-agent system for AI-Tutor - personalized learning coordination"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class Agent:
    def __init__(self, role: str, goal: str):
        self.role = role
        self.goal = goal
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def execute(self, task: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a {self.role}. Goal: {self.goal}"},
                {"role": "user", "content": task}
            ],
            max_tokens=1200,
            temperature=0.7
        )
        return response.choices[0].message.content

def generate_personalized_tutoring(topic: str, grade_level: str, learning_style: str) -> dict:
    """Coordinate tutor and assessor for personalized learning"""

    tutor_agent = Agent("Personal Tutor", "Provide adaptive personalized learning content")
    assessor_agent = Agent("Assessment Specialist", "Create tailored assessments")

    # Generate learning content
    tutor_prompt = f"Create a {learning_style} learning lesson for {topic} at {grade_level} level. Use examples and explanations."
    tutoring_content = tutor_agent.execute(tutor_prompt)

    # Generate assessment
    assess_prompt = f"Create a {learning_style}-friendly assessment for {topic} with feedback guidance"
    assessment = assessor_agent.execute(assess_prompt)

    return {
        "tutoring_content": tutoring_content,
        "assessment": assessment,
        "learning_style": learning_style
    }
