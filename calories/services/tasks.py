from utils.helpers.ai_service import OpenAIClient
from accounts.models import PromptHistory
from ..models import CalorieQA, SuggestedMeal
from rest_framework import serializers
from datetime import timedelta
from django.utils.timezone import now

def generate_calorie_prompt(user, user_prompt: str) -> str:
    try:
        qa = CalorieQA.objects.get(user=user)
        base_context = (
            f"My goal is to {qa.goal}. I weigh {qa.current_weight} lbs and aim for {qa.goal_weight} lbs. "
            f"My activity level is {qa.activity_level}."
            f"I am about {qa.user.age} years old."
            f"My eating style  preference is {qa.eating_style}."
            f"I would like to receive reminders about {qa.reminder}."
            f"Allow smart food suggestions: {qa.allow_smart_food_suggestions}."
            f"My goal timeline is {str(qa.goal_timeline)}."
        )
        full_prompt = f"{base_context}\n\nUser: {user_prompt}"
        return full_prompt
    except CalorieQA.DoesNotExist:
        return user_prompt

def handle_calorie_ai_interaction(user, section, user_prompt: str) -> str:
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
        prompt=user_prompt,
        response=response
    )
    return response

def get_meal_split_from_ai(user_context, calorie_target):
    prompt = f"""
    The user has a daily calorie target of {calorie_target} kcal.
    Their lifestyle: {user_context['lifestyle']}
    Preferences: {user_context['preferences']}
    Workout time: {user_context['workout_time']}

    Suggest how to split the calories among breakfast, lunch, and dinner. 
    Return a JSON like:
    {{
        "breakfast": 0.25,
        "lunch": 0.45,
        "dinner": 0.30
    }}
    """
    # Call OpenAI here and parse the JSON result
    response = OpenAIClient.generate_response(prompt)
    if not response:
        raise serializers.ValidationError(
            {"message": "Failed to get a response from the AI service.", "status": "failed"},
            code=500
        )
        
def build_meal_prompt(calorie_goal, date):
    print("Building meal prompt...")

    return f"""
        You are a health assistant helping users meet their calorie goals through personalized meal planning.

        Today is {date}.
        The user wants to {calorie_goal.goal} by {calorie_goal.goal_timeline}.
        
        "You are a nutrition expert. Based on the following user information, "
        "generate a structured daily meal plan that evenly distributes approximately {calorie_goal.daily_calorie_target} calories "
        "across breakfast, lunch, and dinner. "
        "For each meal, include the meal_type (breakfast/lunch/dinner), meal_name, calories, "
        "and a breakdown of protein (g), carbs (g), and fat (g).\n\n"
        They have a daily calorie target of {calorie_goal.daily_calorie_target} kcal.

        Dietary preferences: {calorie_goal.eating_style or 'None'}
        Activity level: {calorie_goal.activity_level or 'Moderate'}
        User's age: {getattr(calorie_goal.user, 'age', 'Unknown')}
        User's weight: {calorie_goal.current_weight or 'Unknown'}
        User's goal weight: {calorie_goal.goal_weight or 'Unknown'}

        Suggest a detailed meal plan for:
        - Breakfast
        - Lunch
        - Dinner

        Each meal should contain:
        - A meal name
        - Food items
        - Total calories for that meal
        - Macro-nutrient breakdown (protein, fat, carbs in grams)

        Return the response in this JSON format:
        [
        {{
            "meal_type": "breakfast",
            "meal_name": "Oatmeal Banana Bowl",
            "foods": ["Oatmeal", "Banana", "Almond Butter"],
            "calories": 450,
            "protein_g": 18,
            "fat_g": 12,
            "carbs_g": 60
        }},
        {{
            "meal_type": "lunch",
            "meal_name": "Grilled Chicken Quinoa Bowl",
            "foods": ["Chicken breast", "Quinoa", "Spinach", "Avocado"],
            "calories": 700,
            "protein_g": 40,
            "fat_g": 25,
            "carbs_g": 60
        }},
        {{
            "meal_type": "dinner",
            "meal_name": "Salmon Veggie Platter",
            "foods": ["Salmon", "Broccoli", "Sweet Potato"],
            "calories": 650,
            "protein_g": 35,
            "fat_g": 30,
            "carbs_g": 50
        }}
        ]
    """

    
def generate_daily_meal_plan(user_profile, calorie_goal, date):
    prompt = build_meal_prompt(calorie_goal, date)
    response = OpenAIClient.generate_daily_meal_plan(prompt)
    if response is None:
        raise serializers.ValidationError(
            {"message": "Failed to get a response from the AI service.", "status": "failed"},
            code=500
        )
    return response

        
def generate_suggested_meals(calorie_goal_id):
    try:
        calorie_goal = CalorieQA.objects.get(id=calorie_goal_id)
    except CalorieQA.DoesNotExist:
        raise serializers.ValidationError(
            {"message": "Calorie goal not found.", "status": "failed"},
            code=404
        )

    start_date = calorie_goal.created_at
    end_date = calorie_goal.goal_timeline
    daily_target = calorie_goal.daily_calorie_target

    # AI-generated or fallback
    hardcoded_meals = [("breakfast", 0.3), ("lunch", 0.4), ("dinner", 0.3)]
    meals = generate_daily_meal_plan(calorie_goal.user, calorie_goal, start_date)

    for i in range((end_date - start_date).days + 1):
        date = start_date + timedelta(days=i)

        if meals and isinstance(meals[0], dict):
            # AI response: structured dict with actual calories
            for meal in meals:
                SuggestedMeal.objects.create(
                    calorie_goal=calorie_goal,
                    date=date,
                    meal_type=meal['meal_type'],
                    food_item=meal.get('meal_name', 'Example Meal'),
                    calories=meal['calories'],
                    protein=meal.get('protein_g', 0),
                    carbs=meal.get('carbs_g', 0),
                    fats=meal.get('fat_g', 0)
                )
        else:
            # Fallback: use hardcoded ratios
            for meal_type, ratio in hardcoded_meals:
                calories = int(daily_target * ratio)
                SuggestedMeal.objects.create(
                    calorie_goal=calorie_goal,
                    date=date,
                    meal_type=meal_type,
                    food_item=f"{meal_type.title()} Item Example",
                    calories=calories,
                    protein=meal.get('protein_g', 0),
                    carbs=meal.get('carbs_g', 0),
                    fats=meal.get('fat_g', 0)
                )


def generate_suggested_meals_for_the_day(calorie_goal_id, date=None):
    try:
        calorie_goal = CalorieQA.objects.get(id=calorie_goal_id)
    except CalorieQA.DoesNotExist:
        raise serializers.ValidationError(
            {"message": "Calorie goal not configured.", "status": "failed"},
            code=404
        )

    date = date or now().date()
    daily_target = calorie_goal.daily_calorie_target

    # Prevent duplication
    if SuggestedMeal.objects.filter(calorie_goal=calorie_goal, date=date).exists():
        return SuggestedMeal.objects.filter(calorie_goal=calorie_goal, date=date)

    # Call AI-based suggestion
    meals = generate_daily_meal_plan(calorie_goal.user, calorie_goal, date)

    meal_entries = []

    if meals and isinstance(meals[0], dict):
        # AI-based structured meal plan
        for meal in meals:
            meal_entries.append(SuggestedMeal(
                calorie_goal=calorie_goal,
                date=date,
                meal_type=meal['meal_type'],
                food_item=meal.get('meal_name', 'Example Meal'),
                calories=meal['calories'],
                protein=meal.get('protein_g', 0),
                carbs=meal.get('carbs_g', 0),
                fats=meal.get('fat_g', 0)
            ))
    else:
        # Fallback to hardcoded ratios
        default_meals = [("breakfast", 0.3), ("lunch", 0.4), ("dinner", 0.3)]
        for meal_type, ratio in default_meals:
            meal_entries.append(SuggestedMeal(
                calorie_goal=calorie_goal,
                date=date,
                meal_type=meal_type,
                food_item=f"{meal_type.title()} Item Example",
                calories=int(daily_target * ratio),
                protein=meal.get('protein_g', 0),
                carbs=meal.get('carbs_g', 0),
                fats=meal.get('fat_g', 0)
            ))

    # Bulk insert meals for the day
    SuggestedMeal.objects.bulk_create(meal_entries)