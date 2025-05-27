import json
from accounts.choices import Section
from calories.serializers import MealSource
from utils.helpers.ai_service import OpenAIClient
from accounts.models import PromptHistory
import requests
from ..models import *
from rest_framework import serializers
from datetime import timedelta
from django.utils.timezone import now
from datetime import date
from django.db.models import Sum

class MindSpaceAIAssistant:
    def __init__(self, user, mind_space_profile):
        self.user = user
        self.mind_space_profile = mind_space_profile
        
    def build_mood_prompt(self, mood, reflection):
        user = self.user
        mind_space_profile = self.mind_space_profile
        print("Building meal prompt...")

        prompt = f"""
        You are a compassionate mental wellness assistant.

        A user has shared the following information:
        - Mood: "{mood}"
        - Reflection: "{reflection}"
        - Mind Space Profile: {mind_space_profile.frequency_type}
        frequency, goals: {mind_space_profile.goals}

        Based on this input, generate a short, meaningful, and emotionally resonant title that captures the essence of their experience today.

        Respond ONLY with the title as a plain string. Do not add quotes, explanations, or any extra text.
        """
        return prompt
        
    def generate_mood_title_with_base64(self, mood, reflection, base64_image,  text=""):
        prompt = self.build_mood_prompt(mood, reflection)
        
        response = OpenAIClient.chat_with_base64_image(base64_image, text, prompt)
        if not response:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the AI service.", "status": "failed"},
                code=500
            )
        
        return response
        
    def generate_mood_title_with_ai(self, mood, reflection, base_64_image=None, text=""):
        """
        Fetches the mood summary for the user.
        """
        if base_64_image:
            return self.generate_mood_title_with_base64(mood, reflection, base_64_image, text)
        prompt = self.build_mood_prompt(mood, reflection)
        
        response = OpenAIClient.generate_response(prompt)
        if not response:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the AI service.", "status": "failed"},
                code=500
            )
        
        return response
        
    def generate_insights(self, logs: list, count: int = 3) -> list:
        """
        Generates personalized insights for the user based on mood trends.

        :param logs: [{"date": "...", "mood": "...", "reflection": "..."}]
        :param count: How many insights to generate (default: 3)
        :return: A list of strings (insight statements)
        """
        mood_history = "\n".join(
            [f"{log.date}: Mood - {log.mood}. Reflection: {log.reflection}" for log in logs]
        )

        prompt = f"""
            You are an insightful wellness coach.

            A user has logged their mood and reflections over time:
            {mood_history}

            Based on this data, generate {count} unique, helpful **insights**.
            Each insight should be:
            - Actionable (e.g., related to exercise, journaling, social activity)
            - Personalized to their mood patterns
            - Encouraging

            Keep each insight short (1-2 lines). Format them as a bullet list.
            Avoid repeating the same message.
            """
        response = OpenAIClient.generate_response(prompt)
        if not response:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the AI service.", "status": "failed"},
                code=500
            )
        
        return response


    def generate_reflection_note(self, logs: list) -> str:
        """
        Generates a reflection note based on mood/reflection history.
        e.g., health pattern like mood vs. cycle, sleep, hydration, etc.
        
        :param logs: [{"date": "...", "mood": "...", "reflection": "..."}]
        :return: A brief reflection pattern insight (max 2-3 sentences).
        """
        mood_history = "\n".join(
            [f"{log.date}: Mood - {log.mood}. Reflection: {log.reflection}" for log in logs]
        )

        prompt = f"""
            You are a wellness AI helping users discover patterns in their mood logs.

            Here are their logs:
            {mood_history}

            Based on this, write a short **reflection note** that summarizes any recurring patterns.
            For example: headaches often happen before periods, or sadness follows poor sleep, etc.

            Make it short (1-2 lines max) and helpful. Don't repeat exact reflections.
            """
        response = OpenAIClient.generate_response(prompt)
        if not response:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the AI service.", "status": "failed"},
                code=500
            )
        
        return response

            
    def get_affirmation_prompt(self, user_mood: str):
        return f"""
            Based on the fact that the user is feeling {user_mood} today, 
            write a short, uplifting daily affirmation that helps them focus on positivity
            and personal growth.
            Make it encouraging and relevant to their current mood.
            Respond ONLY with the affirmation as a plain string. Do not add quotes, explanations, or any extra text.
            """
            
    def generate_affirmation(self, user_mood: str):
        """
        Generates a daily affirmation based on the user's current mood.
        
        :param user_mood: The user's current mood (e.g., "happy", "sad", "anxious")
        :return: A short, uplifting affirmation string
        """
        prompt = self.get_affirmation_prompt(user_mood)
        
        response = OpenAIClient.generate_response(prompt)
        if not response:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the AI service.", "status": "failed"},
                code=500
            )
        
        return response
