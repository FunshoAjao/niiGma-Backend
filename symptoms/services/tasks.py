

import json
import time
from rest_framework import serializers
from symptoms.models import Symptom, SymptomAnalysis
from utils.helpers.ai_service import OpenAIClient
from core.celery import app as celery_app
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

    analysis, created = SymptomAnalysis.objects.update_or_create(
        session=symptom.session,
        defaults={
            "possible_causes": analysis_text["causes"],
            "advice": analysis_text["advice"]
        }
    )
    logger.info(f"Analysis {'created' if created else 'updated'} for session {symptom.session.id}")
    return

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


    def get_ai_response_with_retry(self, prompt, max_retries=3, delay=2):
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