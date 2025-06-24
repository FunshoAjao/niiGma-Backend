import json
import logging
logger = logging.getLogger(__name__)
from accounts.choices import Section
from utils.helpers.ai_service import OpenAIClient
from accounts.models import PromptHistory
import requests
from ..models import *
from rest_framework import serializers
from datetime import timedelta
from django.utils.timezone import now
from datetime import date
from django.db.models import Sum
from core.celery import app as celery_app
from celery import shared_task


@shared_task
def run_daily_question_sync():
    today = date.today()

    try:
        # Check if there's an entry for today AND it has valid questions
        existing = DailyTriviaSet.objects.filter(date=today).first()
        if existing and existing.questions:
            logger.info(f"✅ Trivia already exists for {today}")
            return

        # (Re)Generate questions
        questions = TriviaAIAssistant().generate_questions_ai(3)
        if not questions:
            logger.warning(f"⚠️ No questions returned by AI for {today}")
            return

        if existing:
            # Update existing empty entry
            existing.questions = questions
            existing.save()
            logger.info(f"♻️ Updated existing DailyTriviaSet for {today}")
        else:
            # Create new entry
            DailyTriviaSet.objects.create(date=today, questions=questions)
            logger.info(f"✅ Created new DailyTriviaSet for {today}")

    except Exception as e:
        logger.exception(f"❌ Failed to sync daily trivia for {today}: {e}")

class TriviaAIAssistant:
    def __init__(self, user:User=None, topic=None):
        self.user = user
        self.topic = topic or "health and wellness"
        
    def build_prompt(self, num_questions=3):
        return f"""
        Generate {num_questions} multiple-choice trivia questions on {self.topic}.
        Each question should include:
        - A question
        - 4 answer choices labeled A-D
        - The correct answer letter
        - A short explanation
        
        Format your response as a JSON list like:
        [
            {{
                "question": "How long does it take to form a habit?",
                "choices": {{"A": "7 days", "B": "21 days", "C": "66 days", "D": "Varies"}},
                "correct_choice": "D",
                "explanation": "While 21 days is a common myth, research shows..."
            }},
            ...
        ]
        """
        
    def generate_questions_ai(self, num_questions=3):
        prompt = self.generate_feature_trivia_prompt(self.user.full_name if self.user is not None else '', num_questions)
        
        raw_response = OpenAIClient.generate_response_list(prompt)

        if not raw_response:
            logger.warning("🟡 AI returned an empty response.")
            return []

        try:
            parsed = json.loads(raw_response)
            if not isinstance(parsed, list):
                logger.warning("🟡 AI returned non-list JSON.")
                return []
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Error parsing AI response: {e}")
            logger.warning(f"Raw response: {raw_response}")
            return []
        
    def generate_feature_trivia_prompt(self, user_first_name: str = "User", num_questions=3) -> str:
        return f"""
        You are a smart health and wellness trivia assistant for a mobile app called Niigma.

        Generate a set of {num_questions} SEMI-HARD multiple choice trivia questions based on these 4 core feature domains:

        1. **Mindspace** – emotional and mental wellbeing, stress, anxiety, journaling, mindfulness.
        2. **Calorie Coach** – food categories, calorie knowledge, healthy diet, macro/micro nutrients.
        3. **Symptom Checker** – common symptoms, probable causes, basic health literacy.
        4. **Ovulation Tracker** – fertility awareness, ovulation signs, hormonal cycle knowledge.

        Your audience is mostly everyday users with interest in health — so questions should:
        - Be **challenging but understandable** (don’t sound like textbook questions).
        - Include 4 choices (A–D) and 1 correct answer.
        - Include a **short explanation** after the correct answer for learning.

        Return the result as a valid Python list of dictionaries:

        ```python
        [
        {{
            "question": "What hormone peaks during ovulation?",
            "choices": ["Estrogen", "LH", "Progesterone", "FSH"],
            "correct_choice": "B",
            "explanation": "Luteinizing hormone (LH) surges before ovulation and triggers the release of the egg."
        }},
        ...
        ]
        Do not include introductions or markdown — only return the list object directly.
        You’re generating this for {user_first_name}, a premium user.
        """
            