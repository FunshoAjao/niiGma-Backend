

import json
from rest_framework import serializers
from utils.helpers.ai_service import OpenAIClient


class SymptomPromptBuilder:
    def __init__(self, user):
        self.user = user

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
        
        response = OpenAIClient.generate_response(prompt)
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
        
        response = OpenAIClient.generate_response(prompt.strip())
        if not response:
            raise serializers.ValidationError(
                {"message": "Failed to get a response from the AI service.", "status": "failed"},
                code=500
            )
        
        return response

