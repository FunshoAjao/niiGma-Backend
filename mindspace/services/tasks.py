import json
from accounts.choices import Section
from calories.serializers import MealSource
from mindspace.services import soundscape_data
from utils.choices import InsightType
from utils.helpers.ai_service import OpenAIClient
from accounts.models import PromptHistory
import requests
from django.utils import timezone
from utils.models import  DailyWindDownQuote, UserAIInsight
from ..models import *
from rest_framework import serializers
from datetime import timedelta
from django.utils.timezone import now
from datetime import date
from django.db.models import Sum
from core.celery import app as celery_app
from celery import shared_task

@celery_app.task(name="create_sound_space_playlist")
def create_sound_space_playlist(mind_space_id):
    try:
        mind_space = MindSpaceProfile.objects.get(id=mind_space_id)
    except MindSpaceProfile.DoesNotExist:
        print(f"MindSpaceProfile with ID {mind_space_id} does not exist.")
        return
    
    soundscape_objects = SoundscapeLibrary.objects.filter(is_active=True)
    SoundscapePlay.objects.bulk_create([
        SoundscapePlay(
            mind_space=mind_space,
            soundscape=s
        )
        for s in soundscape_objects
    ])
    print(f"Created {len(soundscape_objects)} soundscapes for MindSpace ID {mind_space_id}")
    
@shared_task
def generate_daily_wind_down_quotes():
    from datetime import date

    today = date.today()
    moods = MoodChoices.choices

    for mood in moods:
        if DailyWindDownQuote.objects.filter(date=today, mood=mood[0]).exists():
            print(f"Daily wind-down quotes for {today} with mood {mood[0]} already exist.")
            continue

        assistant = MindSpaceAIAssistant()
        quotes = assistant.get_random_quotes_for_user(current_mood=mood)

        try:
            quotes = json.loads(quotes) if isinstance(quotes, str) else quotes
        except Exception:
            quotes = [quotes]

        DailyWindDownQuote.objects.create(date=today, mood=mood[0], quotes=quotes)
        print(f"Created daily wind-down quotes for {today} with mood {mood[0]}")


@shared_task
def generate_weekly_user_insights():
    today = date.today()
    one_week_ago = today - timedelta(days=7)

    users = User.objects.filter(is_active=True, mind_space_profile__isnull=False)
    insights_to_create = []

    for user in users:
        logs = MoodMirrorEntry.objects.filter(
            mind_space__user=user,
            date__date__range=(one_week_ago, today)
        ).order_by("-created_at")[:4]

        if not logs.exists():
            continue
        mood = logs.first().mood or "Unknown"
        
        if user.mood_insights.filter(date=today, insight_type=InsightType.Insight, context_tag=mood).exists():
            print(f"Insights for user {user.email}, mood -{mood} already exist for today.")
            continue
        
        try:
            insights = MindSpaceAIAssistant(user).generate_insights(logs, count=4)
            print(f"Generated insights for user {user.email}")
            

            insights_to_create.append(
                UserAIInsight(
                    user=user,
                    context_tag=mood,
                    date=today,
                    insight_type=InsightType.Insight,
                    insights=insights
                )
            )
        except Exception as e:
            print(f"Error generating insights for user {user.email}: {e}")
            continue

    if insights_to_create:
        UserAIInsight.objects.bulk_create(insights_to_create, ignore_conflicts=True)

class MindSpaceAIAssistant:
    def __init__(self, user=None, mind_space_profile=None):
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
        :return: Respond ONLY with the quotes as a JSON list of strings. Do not add quotes, explanations, or any extra text.
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
            Return the result as a JSON array:
            [
            "Insight 1...",
            "Insight 2...",
            ...
            ]
            """
        response = OpenAIClient.generate_response_list(prompt)
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

    def get_ai_curated_soundscapes(self):
        prompt = "Give me 5 relaxing soundscapes for deep sleep this week, including nature, white noise, and rain variants."
        response = OpenAIClient.generate_response(prompt)
        if not response:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the AI service.", "status": "failed"},
                code=500
            )
        
        return response

    def get_random_quotes_for_user(self, current_mood)-> list:
        prompt = f"""
            You are a motivational AI assistant.
            Generate 7-10 short, uplifting quotes that would inspire someone feeling {current_mood}.
            Make them positive, encouraging, and relevant to mental wellness.
            Respond ONLY with the quotes as a JSON list of strings. Do not add quotes, explanations, or any extra text.
            Generate 7–10 short, calming, and motivational quotes suitable for a user engaging in a wind-down ritual before bedtime. These quotes should help the user reflect, let go of stress, and foster a sense of peace and gratitude.

            The quotes should be:
            - 1–2 short sentences each
            - Gentle, soothing, and emotionally supportive
            - Written in a way that promotes mindfulness, gratitude, and deep relaxation
            - Suitable for someone doing deep breathing (like 4-7-8), journaling, or peaceful visualization

            Example tone:
            - “Inhale peace, exhale stress.”
            - “You did your best today. Let that be enough.”
            - “The day is done. Be proud of yourself.”

            Return the result as a JSON array:
            [
            "Quote 1...",
            "Quote 2...",
            ...
            ]

            """
        response = OpenAIClient.generate_response_list(prompt)
        if not response:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the AI service.", "status": "failed"},
                code=500
            )
        

        return response