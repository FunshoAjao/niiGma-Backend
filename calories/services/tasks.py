from utils.helpers.ai_service import OpenAIClient
from accounts.models import PromptHistory
from ..models import CalorieQA
from rest_framework import serializers

def generate_calorie_prompt(user, user_prompt: str) -> str:
    try:
        qa = CalorieQA.objects.get(user=user)
        base_context = (
            f"My goal is to {qa.goal}. I weigh {qa.current_weight} lbs and aim for {qa.goal_weight} lbs. "
            f"My activity level is {qa.activity_level}."
            f"My eating style  preference is {qa.eating_style}."
            f"I would like to receive reminders about {qa.reminder}."
            f"Allow smart food suggestions: {qa.allow_smart_food_suggestions}."
        )
        full_prompt = f"{base_context}\n\nUser: {user_prompt}"
        return full_prompt
    except CalorieQA.DoesNotExist:
        return user_prompt

def handle_calorie_ai_interaction(user, section, user_prompt: str):
    final_prompt = generate_calorie_prompt(user, user_prompt)
    response = OpenAIClient.generate_response(final_prompt)
    
    if not response:
        raise serializers.ValidationError(
            {"message": "Failed to get a response from the AI service.", "status": "failed"},
            code=500
        )
    PromptHistory.objects.create(
        user=user,
        section=section,
        prompt=final_prompt,
        response=response
    )
    return response
