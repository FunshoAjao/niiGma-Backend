

import json
from rest_framework import serializers
from symptoms.models import Symptom, SymptomAnalysis
from utils.helpers.ai_service import OpenAIClient
from core.celery import app as celery_app
from celery.utils.log import get_task_logger

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
        body_parts = self.symptom.body_areas
        symptom_names = self.symptom.symptom_names
        description = self.symptom.description
        started_on = self.symptom.started_on
        severity = self.symptom.severity
        sensation = self.symptom.sensation
        worsens_with = self.symptom.worsens_with
        notes = self.symptom.notes
        age = self.session.age
        biological_sex = self.session.biological_sex

        symptoms_formatted = ', '.join([f'"{s}"' for s in symptom_names])
        
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
            - Symptoms: {symptoms_formatted}
            - Description: {description}
            - Started On: {started_on}
            - Severity: {severity}
            - Sensation: {sensation}
            - Worsens With: {worsens_with}
            - Notes: {notes}
            - Age: {age}
            - Biological Sex: {biological_sex}
            """

        response = OpenAIClient.generate_response_list(prompt)
        if not response:
            raise serializers.ValidationError(
                {"message": "Failed to get analysis from the AI service.", "status": "failed"},
                code=500
            )
        response = json.loads(response)
        return response