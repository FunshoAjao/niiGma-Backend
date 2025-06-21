import json
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

class TriviaAIAssistant:
    def __init__(self, user):
        self.user = user
        
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
        
    def generate_questions_ai(num_questions=3):
        prompt = f"""
    You are a health and wellness trivia generator.

    Generate {num_questions} multiple-choice questions to help users test their health knowledge.

    For each question, provide:
    - A short question
    - 4 answer choices labeled A, B, C, D
    - The correct choice (just A, B, C, or D)
    - A brief explanation for the correct answer

    Respond in this JSON format:

    [
    {{
        "question": "How many hours of sleep do adults typically need?",
        "choices": {{
        "A": "4–5 hours",
        "B": "6–7 hours",
        "C": "7–9 hours",
        "D": "10–12 hours"
        }},
        "correct_choice": "C",
        "explanation": "Most adults need 7–9 hours of sleep for optimal health."
    }},
    ...
    ]
        """

        response = OpenAIClient.generate_response_list(prompt)
        try:
            return json.loads(response)
        except Exception:
            return []  # Fail-safe empty list if AI fails
            