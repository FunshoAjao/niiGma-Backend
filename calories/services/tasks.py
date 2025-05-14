from utils.helpers.ai_service import OpenAIClient
from accounts.models import PromptHistory
from ..models import CalorieQA

def generate_calorie_prompt(user, user_prompt: str) -> str:
    try:
        qa = CalorieQA.objects.get(user=user)
        base_context = (
            f"My goal is to {qa.goal}. I weigh {qa.weight} lbs and aim for {qa.goal_weight} lbs. "
            f"My activity level is {qa.activity_level}."
        )
        full_prompt = f"{base_context}\n\nUser: {user_prompt}"
        return full_prompt
    except CalorieQA.DoesNotExist:
        return user_prompt

def handle_calorie_ai_interaction(user, section, user_prompt: str):
    final_prompt = generate_calorie_prompt(user, user_prompt)
    response = OpenAIClient.generate_response(final_prompt)

    PromptHistory.objects.create(
        user=user,
        section=section,
        prompt=final_prompt,
        response=response
    )
    return response
