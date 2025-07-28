

import json
import time
from rest_framework import serializers
from calories.models import LoggedMeal
from mindspace.models import MoodMirrorEntry
from ovulations.models import OvulationLog
from symptoms.models import Symptom, SymptomAnalysis
from utils.helpers.ai_service import OpenAIClient
from core.celery import app as celery_app
from django.utils import timezone
from datetime import timedelta
from celery.utils.log import get_task_logger
import logging
logger = get_task_logger(__name__)

@celery_app.task(name="generate_and_save_analysis")
def generate_and_save_analysis(symptom_id):
    try:
        symptom = Symptom.objects.select_related("session").get(id=symptom_id)
    except Symptom.DoesNotExist:
        return
    builder = SymptomPromptBuilder(user=symptom.session.user, symptom=symptom)
    analysis_text = builder.build_analysis_from_symptoms()  # returns formatted string

    _, created = SymptomAnalysis.objects.update_or_create(
        session=symptom.session,
        defaults={
            "possible_causes": analysis_text["causes"],
            "advice": analysis_text["advice"]
        }
    )
    logger.info(f"Analysis {'created' if created else 'updated'} for session {symptom.session.id}")
    
@celery_app.task(name="generate_user_report_and_save_analysis")
def generate_user_report_and_save_analysis(symptom_id):
    try:
        symptom = Symptom.objects.select_related("session").get(id=symptom_id)
    except Symptom.DoesNotExist:
        return
    builder = SymptomPromptBuilder(user=symptom.session.user, symptom=symptom)
    user_report = builder.build_analysis_from_symptoms_user_report()  # returns formatted string

    _, created = SymptomAnalysis.objects.update_or_create(
        session=symptom.session,
        defaults={
            "user_report": user_report,
        }
    )
    logger.info(f"Analysis {'created' if created else 'updated'} for session {symptom.session.id}")

class SymptomPromptBuilder:
    def __init__(self, user, symptom: Symptom=None):
        self.user = user
        self.symptom = symptom
        self.session = symptom.session if symptom is not None else None

    def build_by_body_part(self, body_part):
        """
        Generate a prompt to ask the AI for symptoms associated with a single body part.
        """
        prompt = f"""
        You are a helpful, medically aware assistant.

        A user is describing discomfort in their "{body_part}".

        Return a list of common symptoms typically associated with this body part.

        Format the output as a Python list of strings, like:
        ["Symptom A", "Symptom B", "Symptom C"]

        Do not include any explanations or extra text.
        """
        
        response = OpenAIClient.generate_response_list(prompt)
        if not response:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the AI service.", "status": "failed"},
                code=500
            )
        response = json.loads(response)
        return response
    

    def build_by_multiple_body_parts(self, body_parts):
        """
        Generate a prompt to ask the AI for symptoms grouped by a list of body parts.
        """
        formatted_parts = ", ".join([f'"{part}"' for part in body_parts])
        prompt = f"""
        You are a medically informed assistant.

        A user is reporting issues across multiple body areas: {formatted_parts}.

        For each body part, list the most common symptoms typically associated with it.

        Format the response as a valid Python dictionary where each key is a body part,
        and the value is a list of symptoms. For example:

        {{
            "Head": ["Headache", "Fatigue"],
            "Chest": ["Chest pain", "Shortness of breath"]
        }}

        Do not include explanations or extra information. Only return the dictionary.
        """
        
        response = OpenAIClient.generate_response_list(prompt.strip())
        if not response:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the AI service.", "status": "failed"},
                code=500
            )
        response = json.loads(response)
        return response
    

    def build_analysis_from_symptoms(self):
        """
        Generates analysis using the symptom object, its location, and its session.
        """
        body_parts = str(self.symptom.body_areas).replace('"', '\\"')
        symptom_names = ', '.join([f'"{s}"' for s in self.symptom.symptom_names]).replace('"', '\\"')
        description = str(self.symptom.description).replace('"', '\\"')
        started_on = self.symptom.started_on
        severity = self.symptom.severity
        sensation = self.symptom.sensation
        worsens_with = self.symptom.worsens_with
        notes = self.symptom.notes
        age = self.session.age
        biological_sex = self.session.biological_sex

        prompt = f"""
            You are a helpful medical support assistant.

            Based on the user's symptom report, return a JSON response with:
            1. A list of possible causes (`causes`) — each item must have a `name`, `description`, and `probability` (e.g., "High", "Medium").
            2. A short general advice string under the key `advice`.
            3. A medical disclaimer string under the key `disclaimer`.

            Strictly return a valid JSON object in this format:

            {{
            "causes": [
                {{
                "name": "Condition A",
                "description": "What it is...",
                "probability": "High"
                }},
                ...
            ],
            "advice": "What the user should consider...",
            "disclaimer": "This is not a diagnosis..."
            }}

            Here is the symptom report:

            - Body Part: {body_parts}
            - Symptoms: {symptom_names}
            - Description: {description}
            - Started On: {started_on}
            - Severity: {severity}
            - Sensation: {sensation}
            - Worsens With: {worsens_with}
            - Notes: {notes}
            - Age: {age}
            - Biological Sex: {biological_sex}
        """

         # Call the new retry logic method
        response_json = self.get_ai_response_with_retry(prompt)

        return response_json


    def build_analysis_from_symptoms_user_report(self):
        """
        Builds a contextual and user-friendly health report based on symptoms, mood, ovulation, and meals.
        """
        if not self.symptom or not self.session:
            return "Insufficient data to generate a report."

        user = self.session.user
        today = timezone.now().date()

        # SYMPTOM DATA
        body_parts = str(self.symptom.body_areas).replace('"', '\\"')
        symptom_names = ', '.join(s.title() for s in self.symptom.symptom_names)
        description = self.symptom.description or "No description provided."
        started_on = self.symptom.started_on
        severity = self.symptom.severity or "Not specified"
        sensation = self.symptom.sensation or "Not specified"
        worsens_with = self.symptom.worsens_with or "Not specified"
        notes = self.symptom.notes or "None"
        age = self.session.age
        biological_sex = self.session.biological_sex

        # OVULATION
        recent_ovulation = OvulationLog.objects.filter(
            user=user, date__gte=today - timedelta(days=7)
        ).order_by("-date").first()

        ovulation_context = (
            f"- Date: {recent_ovulation.date}\n"
            f"- Flow: {recent_ovulation.flow}, Discharge: {recent_ovulation.discharge}\n"
            f"- Mood: {recent_ovulation.mood or 'None'}, Symptoms: {', '.join(recent_ovulation.symptoms)}\n"
            f"- Notes: {recent_ovulation.notes or 'None'}"
            if recent_ovulation else "No recent ovulation data logged."
        )

        # MOOD
        recent_moods = MoodMirrorEntry.objects.filter(
            mind_space__user=user, date__gte=today - timedelta(days=7)
        ).order_by("-date")[:3]

        mood_list = [mood.mood for mood in recent_moods] or ["No moods logged"]
        latest_reflection = recent_moods[0].reflection if recent_moods else "No reflection recorded recently."

        # MEALS
        recent_meals = LoggedMeal.objects.filter(
            user=user, date__gte=today - timedelta(days=7)
        ).order_by("-date")[:3]

        meal_summary = (
            "\n".join([
                f"• {meal.date.date()}: {meal.food_item} - {meal.calories} kcal "
                f"(P:{meal.protein}g, C:{meal.carbs}g, F:{meal.fats}g)"
                for meal in recent_meals
            ]) or "No recent meals logged."
        )
        
        prompt = f"""
            You are a helpful and structured health assistant.

            Generate a health report using **this exact structure** below — do not remove or reorder any sections. Your output must strictly follow this format, preserving all numbered sections and headers:

            1.⁠ ⁠How I Am Feeling

            2.⁠ ⁠Description of My Experience

            3.⁠ ⁠My niiGma app Considerations (not a diagnosis)

            4.⁠ ⁠Self-Care Measures Tried (if any)

            5.⁠ ⁠Notes for My Doctor

            ⸻

            Use the data below to write in the user's voice and fill in all five sections:

            — SYMPTOMS —
            - Body Part(s): {body_parts}
            - Symptoms: {symptom_names}
            - Description: {description}
            - Started On: {started_on}
            - Severity: {severity}
            - Sensation: {sensation}
            - Worsens With: {worsens_with}
            - Notes: {notes}

            — PERSONAL PROFILE —
            - Age: {age}
            - Biological Sex: {biological_sex}
            - Affected areas: {body_parts}

            — RECENT OVULATION —
            {ovulation_context}

            — RECENT MOOD —
            - Moods: {", ".join(mood_list)}
            - Reflection: "{latest_reflection}"

            — RECENT MEALS —
            {meal_summary}

            Return your response strictly in the niigma user report style. Do not omit **any** section, and keep formatting clear and user-friendly. Avoid quoting the above; write as if you are the user giving a report.
            """

        # Call your AI service
        response_text = self.get_ai_response_with_retry(prompt, parse_json=False)

        return response_text


    def get_ai_response_with_retry(self, prompt, max_retries=3, delay=2, parse_json=True):
        """
        Tries to get a valid AI response with retry logic for JSONDecodeError.
        Retries up to `max_retries` times with a delay between attempts.
        """
        for attempt in range(max_retries):
            response = OpenAIClient.generate_response_list(prompt)
            
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