import json
import logging
import re
import time
from rest_framework.exceptions import ValidationError
from utils.helpers.cloudinary import CloudinaryFileUpload
logger = logging.getLogger(__name__)
import requests
import base64
from django.core.files.base import ContentFile
from uuid import uuid4
from accounts.choices import Section
from calories.serializers import LoggedMealSerializer, MealSource
from utils.helpers.ai_service import OpenAIClient
from accounts.models import Conversation, PromptHistory, User
import requests
from ..models import MEAL_TYPES, CalorieQA, LoggedMeal, SuggestedMeal, SuggestedWorkout, UserCalorieStreak
from rest_framework import serializers
from datetime import timedelta
from django.utils import timezone
from django.utils.timezone import now
from datetime import date
from django.db.models import Sum
from django.db.models import Q
from celery import shared_task
import string

def extract_grams(text):
    match = re.search(r'([\d.]+)\s*(g|kg|ml|l)', text.lower())
    if match:
        value = float(match.group(1))
        unit = match.group(2)
        if unit == "kg":
            return value * 1000
        elif unit == "l":
            return value * 1000  # assuming density similar to water
        return value
    return None


def clean_string(input_string):
    # Allow only printable characters (removes control characters)
    return ''.join(c for c in input_string if c in string.printable)

@shared_task
def reset_missed_calorie_streaks():
    """
    Resets the calorie streaks for users who did NOT log calorie data yesterday
    and haven't already logged today.
    """
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)

    # Step 1: Get user IDs who logged calories yesterday
    active_user_ids = set(
        LoggedMeal.objects.filter(date=yesterday).values_list("user_id", flat=True)
    )

    # Step 2: Find streaks where user did NOT log yesterday AND hasn't already logged today
    stale_streaks = UserCalorieStreak.objects.filter(
        ~Q(user_id__in=active_user_ids),
        ~Q(last_streak_date=today)
    )

    # Step 3: Update in bulk
    updated = stale_streaks.update(current_streak=0)
    logger.info(f"Reset {updated} calorie streak(s) due to inactivity on {yesterday}")

@shared_task
def update_user_calorie_streak(user_id):
    try:
        user = User.objects.get(id=user_id)
        CalorieAIAssistant(user).update_calorie_streak()
    except User.DoesNotExist:
        return

@shared_task
def async_store_logged_meal_as_suggested(user_id, logged_meal_data):
    try:
        user = User.objects.select_related("calorie_qa").get(id=user_id)
        if not hasattr(user, "calorie_qa"):
            return
        calorie_goal = user.calorie_qa
    except CalorieQA.DoesNotExist:
        return 

    date = logged_meal_data.get("date", timezone.now().date())

    if SuggestedMeal.objects.filter(calorie_goal=calorie_goal, food_item=logged_meal_data["food_item"], date=date).exists():
        return  # Already stored, skip

    SuggestedMeal.objects.create(
        calorie_goal=calorie_goal,
        is_template=True,  # Mark as template for reuse
        meal_type=logged_meal_data["meal_type"],
        food_item=logged_meal_data["food_item"],
        calories=logged_meal_data.get("calories", 0),
        protein=logged_meal_data.get("protein", 0),
        carbs=logged_meal_data.get("carbs", 0),
        fats=logged_meal_data.get("fats", 0)
    )


class CalorieAIAssistant:
    def __init__(self, user: User, logged_meal : LoggedMealSerializer=None):
        self.user = user
        self.logged_meal = logged_meal

    def compare_logged_vs_suggested(self, target_date: date)-> dict:
        results = {}
        user = self.user
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
                date__date=target_date,
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

    def generate_calorie_prompt(self, user_prompt: str) -> str:
        try:
            qa = CalorieQA.objects.get(user=self.user)
            user_profile = f"""
            You are a nutritionist AI helping users meet their health goals through personalized advice.

            Here is the user's profile:
            - Goal: {qa.goal}
            - Current Weight: {qa.current_weight} lbs
            - Goal Weight: {qa.goal_weight} {qa.weight_unit}
            - Activity Level: {qa.activity_level}
            - Age: {qa.user.age}
            - Eating Style Preference: {qa.eating_style or "None"}
            - Wellness Reminder Preference: {qa.reminder or "None"}
            - Smart Food Suggestions Enabled: {"Yes" if qa.allow_smart_food_suggestions else "No"}
            - Goal Timeline: {qa.goal_timeline.strftime('%B %d, %Y') if qa.goal_timeline else "Not specified"}

            The user now says:
            "{user_prompt}"

            Based on the above profile and this message, provide a helpful, context-aware response.
            """
            return user_profile
        except CalorieQA.DoesNotExist:
            # Fallback if no user data exists
            return f"""
            You are a nutritionist AI. The user provided the following input:
            "{user_prompt}"

            Please respond helpfully based only on this input.
            """


    def handle_calorie_ai_interaction(self, section, user_prompt: str) -> str:
        final_prompt = self.generate_calorie_prompt(user_prompt)
        response = OpenAIClient.generate_response(final_prompt)
        
        if not response:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the Niigma AI service.", "status": "failed"},
                code=500
            )
        PromptHistory.objects.create(
            user=self.user,
            section=section,
            prompt=user_prompt,
            response=response
        )
        return response

    def get_meal_split_from_ai(self, user_context, calorie_target):
        prompt = f"""
        You are a nutrition and fitness assistant helping users balance their daily calorie intake across meals.

        The user profile is as follows:
        - Daily Calorie Target: {calorie_target} kcal
        - Lifestyle: {user_context.get('lifestyle', 'Unknown')}
        - Dietary Preferences: {user_context.get('preferences', 'None')}
        - Usual Workout Time: {user_context.get('workout_time', 'Not specified')}

        Based on this, suggest how to optimally split their calories among the three main meals: breakfast, lunch, and dinner.

        Consider these guidelines:
        - Workout time may influence whether more calories should be consumed before or after exercising.
        - A balanced distribution should support energy, digestion, and lifestyle habits.

        Return ONLY a valid JSON object in the following format (do not include any explanation or markdown):

        {{
            "breakfast": 0.30,
            "lunch": 0.40,
            "dinner": 0.30
        }}

        Ensure the values sum up to 1.00 (100% of the daily calories).
        """
        
        response = OpenAIClient.generate_response(prompt)
        if not response:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the Niigma AI service.", "status": "failed"},
                code=500
            )
        
        return response

            
    def get_user_prompt_with_previous_conversation(self, user_input: str, chat_history: str = "") -> str:
        user = self.user
        calorie_qa = getattr(user, 'calorie_qa', None)

        # Graceful fallbacks
        activity_level = getattr(calorie_qa, 'activity_level', 'Not specified')
        eating_style = getattr(calorie_qa, 'eating_style', 'Not specified')
        goal_weight = getattr(calorie_qa, 'goal_weight', 'Unknown')
        weight_unit = getattr(calorie_qa, 'weight_unit', 'kg')
        goal_timeline = getattr(calorie_qa, 'goal_timeline', 'Not specified')

        profile = f"""
            📋 User Profile:
            - Goal: {user.goals}
            - Age: {user.age}
            - Current Weight: {getattr(user, 'weight', 'Unknown')} kg
            - Goal Weight: {goal_weight} {weight_unit}
            - Height: {user.height} {user.height_unit}
            - Wellness Status: {user.wellness_status}
            - Country: {user.country}
            - Goal Timeline: {goal_timeline}
            - Eating Style: {eating_style}
            - Activity Level: {activity_level}
            - Dietary Preference: {getattr(user, 'diet_type', 'Not specified')}
            - Health Conditions: {getattr(user, 'health_conditions', 'None')}
            - Sleep or Stress Notes: {getattr(user, 'sleep_stress_notes', 'Not specified')}
            """
            
        previous_chat = f"🧠 Previous Conversation:\n{chat_history.strip()}\n" if chat_history else ""
        
        # Build final prompt
        prompt = f"""
            You are a compassionate, knowledgeable AI wellness coach helping users with fitness, nutrition, and healthy living.

            {profile}

            {previous_chat}

            🗣 User: {user_input}

            🎯 Your Task:
            Respond as a supportive coach who understands both physical and mental health. Your answer must:
            - Be concise: get to the point, but don't skip important insights, clear, and focused—don’t overwhelm with too much info, but keep all tips actionable and meaningful
            - Be personalized and grounded in their profile and chat history
            - Offer practical suggestions or solutions they can act on now
            - Encourage continuity: based on what they ask, suggest 1–2 related things they might want help with next
            - Be friendly, supportive, and non-judgmental
            - Address both mindset and lifestyle where it makes sense
            - Suggest one or two relevant follow-up actions or questions to keep the conversation going naturally (e.g., “Would you like help building a routine for that?” or “Want me to track your progress this week?”)

            Respond in this JSON format:
            {{
                "title": "[Short, friendly title summarizing the topic]",
                "message": "[Your message to the user. Avoid any markdown or system notes]"
            }}

            Keep the title short and relevant to the user's request (e.g., 'Meal Planning Help' or 'Motivation to Exercise'). Only return valid JSON.
        """
        return prompt.strip()


    
    def get_conversation_context(self, conversation_id, max_turns=2):
        history = PromptHistory.objects.filter(
            user=self.user,
            conversation_id=conversation_id
        ).order_by('-created_at')[:max_turns]  # most recent messages

        # Reverse to get chronological order
        history = reversed(history)

        formatted = ""
        for entry in history:
            formatted += f"User: {entry.prompt}\nAI: {entry.response}\n"
        return formatted.strip()

    
    def get_user_prompt(self, user_input: str) -> str:
        user = self.user
        calorie_qa = getattr(user, 'calorie_qa', None)

        # Graceful fallbacks
        activity_level = getattr(calorie_qa, 'activity_level', 'Not specified')
        eating_style = getattr(calorie_qa, 'eating_style', 'Not specified')
        goal_weight = getattr(calorie_qa, 'goal_weight', 'Unknown')
        weight_unit = getattr(calorie_qa, 'weight_unit', 'kg')
        goal_timeline = getattr(calorie_qa, 'goal_timeline', 'Not specified')
        
        prompt = f"""
            You are a compassionate, knowledgeable AI wellness coach helping users with fitness, nutrition, and healthy living. Use the details below to personalize your response.

            📋 **User Profile**:
            - Goal: {user.goals}
            - Age: {user.age}
            - Current Weight: {getattr(user, 'weight', 'Unknown')} kg
            - Goal Weight: {goal_weight} {weight_unit}
            - Height: {user.height} {user.height_unit}
            - Wellness Status: {user.wellness_status}
            - Country: {user.country}
            - Goal Timeline: {goal_timeline}
            - Eating Style: {eating_style}
            - Activity Level: {activity_level}
            - Dietary Preference: {getattr(user, 'diet_type', 'Not specified')}
            - Health Conditions: {getattr(user, 'health_conditions', 'None')}
            - Sleep or Stress Notes: {getattr(user, 'sleep_stress_notes', 'Not specified')}

            🗣 **User Message**:
            "{user_input}"

            🎯 **Your Task**:
            Respond as a supportive coach who understands both physical and mental health. Your answer should:
            - Be personalized and grounded in their profile
            - Offer encouragement and actionable tips
            - Be friendly, positive, and non-judgmental
            - Address both lifestyle and mindset when appropriate

            Respond with just your message to the user. Avoid any markdown or system notes.
            """
        return prompt


            
    def chat_with_ai(self, user_context, conversation_id: uuid4, base_64_image=None, text=""):
        if base_64_image:
            return self.chat_with_ai_with_base64(user_context, base_64_image, text)
        
        # Build conversation context if it exists
        chat_history = self.get_conversation_context(conversation_id) if conversation_id else ""

        # Compose full prompt with profile + history
        prompt = self.get_user_prompt_with_previous_conversation(user_context, chat_history)
        
        response = OpenAIClient.generate_response(prompt)
        try:
            response = response.strip()
            response_cleaned = clean_string(response)
            response_cleaned = response.replace("\\n", "\n").replace("\\t", "\t")

            parsed = json.loads(response_cleaned)

            title = parsed.get("title", "AI Conversation")
            message = parsed.get("message", response_cleaned)
        except json.JSONDecodeError as e:
            print("Error parsing JSON:", e)  # Log the error for debugging
            logger.error(f"JSON parsing error: {e}")
            title = "AI Conversation"
            message = response_cleaned  # Default to raw response if JSON parsing fails

        # If no message was found, raise an error
        if not message:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the Niigma AI service.", "status": "failed"},
                code=500
            )
        
        if not conversation_id:
            conversation = Conversation.objects.create(user=self.user, title=f"{title}")
        else:
            conversation = Conversation.objects.get(id=conversation_id)

        # Save prompt + response
        PromptHistory.objects.create(
            user=self.user,
            section=Section.NONE,
            prompt=user_context,
            response=message,
            conversation=conversation
        )

        return message, conversation.id

    def chat_with_ai_with_base64(self, user_context, base64_image,  text=""):
        prompt = self.get_user_prompt( user_context)
        
        response = OpenAIClient.chat_with_base64_image(base64_image, text, prompt)
        if not response:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the Niigma AI service.", "status": "failed"},
                code=500
            )
        PromptHistory.objects.create(
                    user=self.user,
                    section=Section.NONE,
                    prompt=user_context,
                    response=response
                )
        return response
            
    def build_meal_prompt(self, calorie_goal, date):
        user = self.user
        print("Building meal prompt...")

        prompt = f"""
        You are a certified nutrition expert helping users reach their health goals through personalized daily meal plans.

        Date: {date}
        User's Goal: {calorie_goal.goal}
        Target Date: {calorie_goal.goal_timeline.strftime('%B %d, %Y') if calorie_goal.goal_timeline else 'Not specified'}
        Daily Calorie Target: {calorie_goal.daily_calorie_target} kcal

        User Profile:
        - Age: {user.age or 'Unknown'}
        - Gender: {getattr(user, 'gender', 'Unknown')}
        - Weight: {calorie_goal.current_weight or 'Unknown'} {calorie_goal.weight_unit or ''}
        - Goal Weight: {calorie_goal.goal_weight or 'Unknown'} {calorie_goal.weight_unit or ''}
        - Height: {getattr(user, 'height', 'Unknown')} {getattr(user, 'height_unit', '')}
        - Activity Level: {calorie_goal.activity_level or 'Moderate'}
        - Dietary Preference: {calorie_goal.eating_style or 'None'}
        - Wellness Status: {user.wellness_status or 'Unknown'}
        - Country: {user.country or 'Unknown'}

        Your task:
        Design a balanced meal plan for the user, distributing approximately {calorie_goal.daily_calorie_target} kcal across:
        - Breakfast
        - Lunch
        - Dinner

        For each meal, include:
        - meal_type (breakfast/lunch/dinner)
        - meal_name (e.g. "Oatmeal Banana Bowl")
        - a list of key foods (e.g. ["Oatmeal", "Banana", "Almond Butter"])
        - total calories for the meal
        - macronutrient breakdown: protein_g, fat_g, carbs_g

        Return ONLY a valid JSON array in the following format:
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

        Do not return anything other than the JSON.
        """

        return prompt


    def build_suggested_workout_prompt(self, calorie_target, date):
        user = self.user
        qa = getattr(user, "calorie_qa", None)

        activity_level = getattr(qa, "activity_level", "Moderate")
        goal = getattr(qa, "goal", "Improve fitness")

        return f"""
        You are a certified fitness coach assisting users in achieving their daily calorie burn targets with realistic, effective workouts.

        Date: {date}
        User's Target: Burn approximately {calorie_target} kcal today.

        User Profile:
        - Age: {getattr(user, 'age', 'Unknown')}
        - Fitness Level: {activity_level}
        - Goal: {goal}
        - Location: Home (assume no equipment available)
        - Preferred workout duration: 30–45 minutes

        Based on this profile, suggest ONE highly suitable workout routine.

        The response must be a valid JSON object with the following structure:

        {{
            "workout_name": "Full-Body HIIT Circuit",
            "description": "A high-intensity interval training session including jumping jacks, burpees, mountain climbers, and squats, performed in circuits.",
            "duration_minutes": 35,
            "estimated_calories_burned": 420,
            "intensity": "high"
        }}

        Only return the JSON object. Avoid explanations or additional text.
        """


        
    def generate_daily_meal_plan(self, calorie_goal, date):
        prompt = self.build_meal_prompt(calorie_goal, date)
        response = OpenAIClient.generate_daily_meal_plan(prompt)
        if response is None:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the Niigma AI service.", "status": "failed"},
                code=500
            )
        return response

    def get_ai_response_with_retry(self, prompt, max_retries=3, delay=2, parse_json=True):
        """
        Tries to get a valid AI response with retry logic for JSONDecodeError.
        Retries up to `max_retries` times with a delay between attempts.
        """
        for attempt in range(max_retries):
            response = OpenAIClient.generate_daily_meal_plan(prompt)
            
            if not response:
                raise serializers.ValidationError(
                    {"message": "Failed to get analysis from the AI service.", "status": "failed"},
                    code=500
                )

            logging.debug(f"Attempt {attempt + 1}: Raw AI Response:")
            logging.debug(response)
            
            if not parse_json:
                return response.strip()

            try:
                response_json = json.loads(response)
                return response_json  # Return if successful
            except json.JSONDecodeError as e:
                logging.error(f"JSONDecodeError: {e}")
                logging.error("Response that caused the error:")
                logging.error(response)

                # If it's the last attempt, raise the error
                if attempt == max_retries - 1:
                    raise serializers.ValidationError(
                        {"message": "Failed to parse AI response. Invalid JSON format.", "status": "failed"},
                        code=500
                    )

                # Wait before retrying
                time.sleep(delay)
                logging.info(f"Retrying... (Attempt {attempt + 2})")

        # If all retries fail, return an error
        raise serializers.ValidationError(
            {"message": "Failed to process the analysis after multiple attempts.", "status": "failed"},
            code=500
        )
            
    def generate_suggested_meals(self, calorie_goal_id):
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
        meals = self.generate_daily_meal_plan(calorie_goal, start_date)

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


    def generate_suggested_meals_for_the_day(self, calorie_goal_id, date=None):
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
        meals = self.generate_daily_meal_plan(calorie_goal, date)

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
                    protein=0,
                    carbs=0,
                    fats=0
                ))


        # Bulk insert meals for the day
        SuggestedMeal.objects.bulk_create(meal_entries)
        
    def _extract_grams_from_serving_size(self, serving_size_str):
        # e.g. "30g", "1 slice (25 g)", etc.
        match = re.search(r"(\d+(?:\.\d+)?)\s?g", serving_size_str.lower())
        return float(match.group(1)) if match else None
    
    def _get_weight_in_grams(self, unit, food_name, servings, product):
        # Default weight if we can't find any
        default_grams = 100

        if unit == "gram":
            return servings  # user specified grams directly

        elif unit == "serving":
            serving_size = product.get("serving_size", "")
            grams = self._extract_grams_from_serving_size(serving_size)
            return grams * servings if grams else default_grams * servings

        elif unit == "slice":
            SLICE_TO_GRAMS = {
                "bread": 30,
                "cheese": 20,
                "cake": 80,
            }
            food_key = food_name.lower()
            grams_per_slice = SLICE_TO_GRAMS.get(food_key, default_grams)
            return grams_per_slice * servings

        return default_grams * servings
    
    def get_food_by_barcode(self, barcode: str) -> dict:
        try:
            response = requests.get(f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json")
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") != 1:
                    raise serializers.ValidationError(
                        {"message": "No product found for the given barcode.", "status": "failed"},
                        code=400
                    )

                product = data.get("product", {})

                if not product or not product.get("nutriments"):
                    raise serializers.ValidationError(
                        {"message": "Product information is incomplete or missing for this barcode.", "status": "failed"},
                        code=400
                    )

                logger.info(f"name: {product.get('product_name', 'Unknown')}")
                print(f"name of the product logged by barcode: {product.get('product_name', 'Unknown')}")

                nutriments = product.get("nutriments", {})
                food_name = product.get("product_name", "Unknown")

                # Nutrients per 100g
                kcal = float(nutriments.get("energy-kcal_100g", 0))
                protein = float(nutriments.get("proteins_100g", 0))
                carbs = float(nutriments.get("carbohydrates_100g", 0))
                fats = float(nutriments.get("fat_100g", 0))

                # Try to infer total grams from product data
                total_grams = None
                quantity_str = product.get("quantity", "")
                product_quantity = product.get("product_quantity")  # numeric in grams or ml
                serving_size = product.get("serving_size", "")

                if product_quantity:
                    total_grams = float(product_quantity)
                elif extract_grams(quantity_str):
                    total_grams = extract_grams(quantity_str)
                elif extract_grams(serving_size):
                    total_grams = extract_grams(serving_size)

                # Fallback to your method if still unknown
                if not total_grams:
                    total_grams = self._get_weight_in_grams(
                        self.logged_meal['measurement_unit'],
                        food_name,
                        self.logged_meal['number_of_servings_or_gram_or_slices'],
                        product
                    )

                multiplier = total_grams / 100

                return {
                    "name": food_name,
                    "calories": round(kcal * multiplier, 2),
                    "protein": round(protein * multiplier, 2),
                    "carbs": round(carbs * multiplier, 2),
                    "fats": round(fats * multiplier, 2),
                }

            else:
                logger.error(f"Barcode lookup failed with status {response.status_code}")
                raise ConnectionError("Unable to fetch data from food database.")

        except ValidationError:
            raise  # Re-raise so DRF handles it cleanly

        except requests.exceptions.RequestException as e:
            logger.error(f"RequestException: {e}")
            raise ValidationError(
                {"message": "Could not connect to barcode nutrition API. Please try again later.", "status": "failed"}, code=400
            )

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise ValidationError(
                {"message": "Something went wrong while processing the barcode.", "status": "failed"}, code=400
            )
    
    def extract_food_items_from_meal_source(self, meal_source, serving_count=1,
                                            measurement_unit="serving", food_description=None,
                                            barcode=None, scanned_image=None) -> dict:
        if meal_source == MealSource.Barcode:
            food_item = self.get_food_by_barcode(barcode)
            print(f"Food item extracted from barcode: {food_item}")
            if food_item:
                return {
                    "food_name": food_item["name"],
                    "calories": food_item["calories"],
                    "protein": food_item["protein"],
                    "carbs": food_item["carbs"],
                    "fats": food_item["fats"]
                }
                
        elif meal_source == MealSource.Manual:
            return self.estimate_nutrition_with_ai(food_description, serving_count, measurement_unit)
        
        elif meal_source == MealSource.Scanned:
            return self.analyze_food_image(scanned_image)
        
        else: return {}
        
    def extract_sample_food_items_from_meal_source(
        self, 
        meal_source, 
        serving_count=1,
        measurement_unit="serving", 
        food_description=None, 
        barcode=None, 
        scanned_image=None
    ) -> dict:
        if meal_source == MealSource.Barcode:
            food_item = self.get_food_by_barcode(barcode)
            if food_item:
                return {
                    "food_name": food_item["name"],
                    "calories": food_item["calories"],
                    "protein": food_item["protein"],
                    "carbs": food_item["carbs"],
                    "fats": food_item["fats"],
                }

        elif meal_source == MealSource.Manual:
            return self.estimate_food_nutrition_from_description(
                food_description, measurement_unit
            )

        elif meal_source == MealSource.Scanned:
            return self.analyze_food_image(scanned_image)

        return {}

    def estimate_food_nutrition_from_description(self, description: str, measurement_unit: str = "serving") -> dict:
        prompt = f"""
        You are a nutrition assistant.

        A user described the following food: "{description}"

        Please provide a structured response in JSON with:
        - "food_name": Name/title of the food
        - "calories": Estimated calories for 1 {measurement_unit}
        - "protein": Grams of protein per {measurement_unit}
        - "carbs": Grams of carbs per {measurement_unit}
        - "fats": Grams of fat per {measurement_unit}
        - "number_of_servings_or_weight_in_grams_or_number_of_slices": Estimated serving weight in grams or slices or number of servings (if applicable)

        Respond strictly in this format:
        {{
            "food_name": "...",
            "title":"...",
            "calories": ...,
            "protein": ...,
            "carbs": ...,
            "fats": ...,
            "number_of_servings_or_weight_in_grams_or_number_of_slices": ...
        }}
        """
        
        response = OpenAIClient.chat(prompt)
        serving_count: int = 1
        try:
            data = json.loads(response)
            # Multiply by serving count if needed
            return {
                "food_name": data["food_name"],
                "title": data["title"],
                "calories": round(data["calories"] * serving_count),
                "protein": round(data["protein"] * serving_count),
                "carbs": round(data["carbs"] * serving_count),
                "fats": round(data["fats"] * serving_count),
                "number_of_servings_or_weight_in_grams_or_number_of_slices": data.get("number_of_servings_or_weight_in_grams_or_number_of_slices", None)
            }

        except (KeyError, ValueError) as e:
            raise serializers.ValidationError(
                {"message": "Failed to extract nutrition info from Niigma AI response.", "error": str(e)},
                code=500
            )
        
    
    def estimate_nutrition_with_ai(self, description, number_of_servings_or_gram_or_slices, measurement_unit) -> dict:
        user_country = getattr(self.user, "country", "Canada")
        prompt = f"""
            You are a knowledgeable nutritionist.

            Estimate total **calories**, **protein (g)**, **fats (g)**, and **carbohydrates (g)** for the following meal:

            **Description:** "{description}"

            The user consumed **{number_of_servings_or_gram_or_slices} {measurement_unit}(s)** 
            (e.g., 1 serving ≈ 250g if known).

            Assume standard portion sizes in {user_country} unless otherwise specified.

            Respond ONLY in JSON with this exact format:
            {{
            "calories": 123,
            "protein": 4,
            "fats": 2,
            "carbs": 25
            }}
            """

        # Call the AI service to generate nutrition estimate
        nutrition = OpenAIClient.generate_response(prompt)
        
        if not nutrition:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the Niigma AI service.", "status": "failed"},
                code=500
            )
            
        # Parse the JSON string into a Python dict
        try:
            nutrition = json.loads(nutrition)
        except json.JSONDecodeError:
            raise serializers.ValidationError(
                {"message": "Niigma AI response could not be parsed as valid JSON.", "status": "failed"},
                code=500
            )
        
        return self._sanitize_nutrition_data(nutrition)

        
    def _sanitize_nutrition_data(self, nutrition: dict) -> dict:
        def clean(value):
            try:
                val = float(value)
                return max(0, round(val))  # No negatives, round to int
            except (ValueError, TypeError):
                return 0

        return {
            "calories": clean(nutrition.get("calories")),
            "protein": clean(nutrition.get("protein")),
            "fats": clean(nutrition.get("fats")),
            "carbs": clean(nutrition.get("carbs")),
        }


    def generate_health_insight(self, calorie_goal, total_calories, macros_percent, date):
        prompt = f"""
        You are a fitness and nutrition expert.

        Today is {date}. A user has the following nutrition summary:

        - Calorie goal: {calorie_goal} kcal
        - Calories consumed: {total_calories} kcal
        - Macros percentage: {macros_percent}

        Based on this, generate a short, helpful health insight (1-2 sentences) that encourages the user to make better food choices. Be supportive and practical. Avoid repeating the numbers exactly.

        Example: "You’re doing great, but try to include more protein in your meals to support muscle repair."

        Respond with only the insight sentence.
        """

        response = OpenAIClient.generate_response(prompt)
        
        if not response:
            return "Unable to generate health insight at the moment."
        return response

            
    def generate_suggested_workout_with_ai(self, calorie_target, date):
        prompt = self.build_suggested_workout_prompt(calorie_target, date)
        workout_calorie_data = OpenAIClient.generate_daily_meal_plan(prompt)
        if workout_calorie_data is None:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the Niigma AI service.", "status": "failed"},
                code=500
            )
        
        SuggestedWorkout.objects.update_or_create(
                calorie_goal=self.user.calorie_qa,
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

    def estimate_logged_workout_calories(self, workout_description, duration, description, intensity, steps=None):
        user = self.user
        prompt = f"""
        You are a fitness assistant.

        A user performed the following activity:

        - Activity Description: "{workout_description}"
        - Duration: {duration} minutes
        - User Age: {getattr(user, 'age', 'Unknown')}
        - Weight: {user.calorie_qa.current_weight} {user.calorie_qa.weight_unit}
        - Height: {getattr(user, 'height', 'Unknown')} {getattr(user, 'height_unit', '')}
        - Activity Level: {user.calorie_qa.activity_level}
        - Number of Steps: {steps if steps is not None else 'Unknown'}
        - Additional Notes: {description}
        - Intensity: {intensity}

        Please estimate the total calories burned as an integer number only. Respond with just the number, no units or extra text.
        """

        response = OpenAIClient.chat(prompt)
        try:
            calories = int(response.strip())
        except (ValueError, AttributeError):
            raise serializers.ValidationError(
                {"message": "Failed to parse calorie estimate from Niigma AI response.", "status": "failed"},
                code=500
            )
        return calories
    
    def estimate_sample_logged_workout_details(self, workout_description: str, notes: str = "") -> dict:
        user = self.user

        prompt = f"""
        You are a fitness assistant.

        A user performed the following activity: "{workout_description}"

        User Details:
        - Age: {getattr(user, 'age', 'Unknown')}
        - Weight: {user.calorie_qa.current_weight} {user.calorie_qa.weight_unit}
        - Height: {getattr(user, 'height', 'Unknown')} {getattr(user, 'height_unit', '')}
        - Activity Level: {user.calorie_qa.activity_level}

        Additional Notes: {notes}

        Based on the description, provide an estimated summary of the workout including:
        - Title (short name of the activity)
        - Duration (in minutes)
        - Intensity (low, medium, or high)
        - Estimated Calories Burned (as an integer)
        - Estimated Steps (if it involves walking or running, else null)

        Respond strictly in JSON format:
        {{
            "title": "...",
            "duration": ...,
            "intensity": "...",
            "estimated_calories_burned": ...,
            "steps": ...
        }}
        """

        response = OpenAIClient.chat(prompt)

        try:
            workout_data = json.loads(response)
            required_keys = ["title", "duration", "intensity", "estimated_calories_burned", "steps"]
            if not all(k in workout_data for k in required_keys):
                raise ValueError("Missing one or more required fields in Niigma AI response.")

            return workout_data

        except (ValueError, AttributeError) as e:
            raise serializers.ValidationError(
                {"message": "Failed to extract workout data from Niigma AI response.", "error": str(e), "status": "failed"},
                code=500
            )

    def analyze_food_image(self, base64_image=None):
        image_file = self.save_image_from_base64(base64_image)
        file_name = f'{self.user.first_name} {self.user.id}-meal_image'
        image_url = CloudinaryFileUpload().upload_file_to_cloudinary(image_file, file_name)
        nutrition_info = self.analyze_meal_with_ai(image_url)
        nutrition_info['image_url'] = image_url
        
        return nutrition_info
        
    def save_image_from_base64(self, base64_str):
        """Decode base64 image and prepare as file for upload"""
        format_, imgstr = base64_str.split(';base64,')
        ext = format_.split('/')[-1]
        return ContentFile(base64.b64decode(imgstr), name='meal_image.' + ext)

    
    def analyze_meal_with_ai(self, image_url: str) -> dict:
        prompt = (
            "You're a nutritionist. Analyze this food image. "
            "Respond strictly in JSON format with the following keys: "
            "'food_name', 'calories', 'protein', 'carbs', 'fats', 'servings'. "
            "All values should be numbers except food_name. Assume a common serving size."
            "Do NOT include any markdown, backticks, or extra text—return ONLY the JSON object."
        )

        response = OpenAIClient.chat_with_base64_image(image_url, prompt)

        if not response or not isinstance(response, str):
            raise serializers.ValidationError(
                {"message": "Empty or invalid response from Niigma AI", "status": "failed"},
                code=500
            )

        try:
            print("Raw AI Response:", response)  # Debug log
            nutrition = json.loads(response.strip())
            return nutrition

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            raise serializers.ValidationError(
                {
                    "message": "Invalid format returned from Niigma AI. Please check the input image or try again.",
                    "error": str(e),
                    "raw_response": response,
                    "status": "failed"
                },
                code=400
            )

    def update_calorie_streak(self):
        user = self.user
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        streak, _ = UserCalorieStreak.objects.get_or_create(user=user)
        calorie_qa = getattr(user, "calorie_qa", None)
        if not calorie_qa:
            return

        if streak.last_streak_date == today:
            return  # already counted today

        if streak.last_streak_date == yesterday:
            streak.current_streak += 1
        else:
            streak.current_streak = 1

        streak.longest_streak = max(streak.longest_streak, streak.current_streak)
        streak.last_streak_date = today
        streak.save()