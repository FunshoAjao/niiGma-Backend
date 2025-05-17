from accounts.choices import Section
from calories.serializers import MealSource
from utils.helpers.ai_service import OpenAIClient
from accounts.models import PromptHistory
import requests
from ..models import MEAL_TYPES, CalorieQA, LoggedMeal, SuggestedMeal, SuggestedWorkout
from rest_framework import serializers
from datetime import timedelta
from django.utils.timezone import now
from datetime import date
from django.db.models import Sum

def compare_logged_vs_suggested(user, target_date: date)-> dict:
    results = {}

    for meal_type, _ in MEAL_TYPES:
        # Get suggested meal
        suggested = SuggestedMeal.objects.filter(
            calorie_goal__user=user,
            date__date=target_date,
            meal_type=meal_type
        ).aggregate(
            total_calories=Sum('calories'),
            total_protein=Sum('protein'),
            total_carbs=Sum('carbs'),
            total_fats=Sum('fats'),
        )

        # Get logged meal
        logged = LoggedMeal.objects.filter(
            user=user,
            date=target_date,
            meal_type=meal_type
        ).aggregate(
            total_calories=Sum('calories'),
            total_protein=Sum('protein'),
            total_carbs=Sum('carbs'),
            total_fats=Sum('fats'),
        )

        results[meal_type] = {
            "suggested": suggested,
            "logged": logged,
            "difference": {
                "calories": (logged["total_calories"] or 0) - (suggested["total_calories"] or 0),
                "protein": (logged["total_protein"] or 0) - (suggested["total_protein"] or 0),
                "carbs": (logged["total_carbs"] or 0) - (suggested["total_carbs"] or 0),
                "fats": (logged["total_fats"] or 0) - (suggested["total_fats"] or 0),
            }
        }

    return results

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
        
def get_user_prompt(user, prompt)-> str:
    prompt = f"""
        You are a helpful AI fitness and health assistant.

        Here is the user's profile:
        - Goal: {user.goals}
        - Current Weight: {user} kg
        - Current Height: {user.height} kg
        - Wellnesss Status: {user.wellness_status}
        - Country: {user.country}
        - Age: {user.age}

        The user says:
        "{prompt}"

        Based on the user's profile, respond helpfully and conversationally.
    """
    return prompt
        
def chat_with_ai(user, user_context, base_64_image=None, text=""):
    if base_64_image:
        return chat_with_ai_with_base64(user, user_context, base_64_image, text)
    prompt = get_user_prompt(user, user_context)
    # Call OpenAI here and parse the JSON result
    response = OpenAIClient.generate_response(prompt)
    if not response:
        raise serializers.ValidationError(
            {"message": "Failed to get a response from the AI service.", "status": "failed"},
            code=500
        )
    PromptHistory.objects.create(
                user=user,
                section=Section.NONE,
                prompt=user_context,
                response=response
            )
    return response

def chat_with_ai_with_base64(user, user_context, base64_image,  text=""):
    prompt = get_user_prompt(user, user_context)
    
    response = OpenAIClient.chat_with_base64_image(base64_image, text, prompt)
    if not response:
        raise serializers.ValidationError(
            {"message": "Failed to get a response from the AI service.", "status": "failed"},
            code=500
        )
    PromptHistory.objects.create(
                user=user,
                section=Section.NONE,
                prompt=user_context,
                response=response
            )
    return response
        
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
        User's current country: {calorie_goal.user.country or 'Unknown'}

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

def build_suggested_workout_prompt(user, calorie_target, date):
    return f"""
        You are a fitness coach helping users meet their daily calorie burn targets through simple workout routines.

        Today's date is {date}.

        The user has a calorie goal to burn approximately **{calorie_target} kcal** today through physical activity.

        Please suggest **one effective workout routine** that fits the user's profile:
        - Age: {user.age if hasattr(user, 'age') else "Unknown"}
        - Fitness Level: {user.calorie_qa.activity_level}
        - Goal: {user.calorie_qa.goal}
        - Available equipment: None (assume home-friendly workout)
        - Preferred workout duration: 30–45 minutes (can be adjusted)

        Provide:
        - **Workout name**
        - **Short description**
        - **Estimated duration (in minutes)**
        - **Estimated calories burned**

        Respond in the following JSON format:

        {{
        "workout_name": "Full-Body HIIT Circuit",
        "description": "A high-intensity interval training session including jumping jacks, burpees, mountain climbers, and squats, performed in circuits.",
        "duration_minutes": 35,
        "estimated_calories_burned": 420
        "duration_minutes": 35,
        "intensity": --> INTENSITY_CHOICES = [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ]
        }}
    """

    
def generate_daily_meal_plan(calorie_goal, date):
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
    meals = generate_daily_meal_plan(calorie_goal, date)

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
    
    
def extract_food_items_from_meal_source(meal_source, food_description=None) -> dict:
    if meal_source == MealSource.Barcode:
        barcode = meal_source.get("barcode")
        food_item = get_food_by_barcode(barcode)
        if food_item:
            return {
                "name": food_item["name"],
                "calories": food_item["calories"],
                "protein": food_item["protein"],
                "carbs": food_item["carbs"],
                "fat": food_item["fat"]
            }
            
    elif meal_source == MealSource.Manual:
        return estimate_nutrition_with_ai(food_description)
    
    elif meal_source == MealSource.Scanned:
        return analyze_food_image(meal_source.get("scanned_image"))
    
    else: return {}
    
    
def estimate_nutrition_with_ai(description) -> dict:
        prompt = f"""
        Estimate the total calories, protein (g), fats (g), and carbs (g) for: {description}.
        Provide a JSON response with keys: calories, protein, fats, carbs.
        """
        
        nutrition = OpenAIClient.generate_daily_meal_plan(prompt)
        return {
                "calories": nutrition.get("calories", 0),
                "protein": nutrition.get("protein", 0),
                "fats": nutrition.get("fats", 0),
                "carbs": nutrition.get("carbs", 0)
            }
        
def generate_suggested_workout_with_ai(user, calorie_target, date):
    prompt = build_suggested_workout_prompt(user, calorie_target, date)
    workout_calorie_data = OpenAIClient.generate_daily_meal_plan(prompt)
    if workout_calorie_data is None:
        raise serializers.ValidationError(
            {"message": "Failed to get a response from the AI service.", "status": "failed"},
            code=500
        )
    print("Workout data:", workout_calorie_data)
    SuggestedWorkout.objects.update_or_create(
            calorie_goal=user.calorie_qa,
            date=date,
            defaults={
                "duration_minutes": workout_calorie_data["duration_minutes"],
                "intensity": workout_calorie_data["intensity"],
                "title": workout_calorie_data["workout_name"],
                "description": workout_calorie_data["description"],
                "estimated_calories_burned": workout_calorie_data["estimated_calories_burned"]
            }
        )
    return  None

def estimate_logged_workout_calories(workout_description, duration, user):
    prompt = f"""
        You are a fitness assistant. A user has performed the following activity:

        - Description: "{workout_description}"
        - Duration: {duration} minutes
        - Age: {user.age if hasattr(user, 'age') else "Unknown"}
        - Weight: {user.calorie_qa.current_weight} kg
        - Activity level: {user.calorie_qa.activity_level}

        Estimate how many calories they likely burned. Return a number (integer only), without units or extra text.
    """
    workout_estimated_calories = OpenAIClient.chat(prompt)
    calories = int(workout_estimated_calories.strip())
    return calories

      
def get_food_by_barcode(barcode)-> dict:
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    response = requests.get(url)
    if response.status_code == 200:
        product = response.json().get("product", {})
        return {
            "name": product.get("product_name", "Unknown Product"),
            "calories": product.get("nutriments", {}).get("energy-kcal_100g", 0),
            "protein": product.get("nutriments", {}).get("proteins_100g", 0),
            "carbs": product.get("nutriments", {}).get("carbohydrates_100g", 0),
            "fat": product.get("nutriments", {}).get("fat_100g", 0),
        }
    return {}

def analyze_food_image(image_base64=None):
    # 1. Send to Google Cloud Vision -> get labels
    # 2. Send label to Nutritionix API to get calories
    # Pseudocode due to API complexity
    food_name = "grilled chicken"  # label from Vision
    # Then call Nutritionix API to get nutrition info
    return {
        "name": food_name,
        "calories": 300,
        "protein": 25,
        "carbs": 5,
        "fat": 10,
    }

