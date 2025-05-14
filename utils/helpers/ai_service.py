from openai import OpenAI
from rest_framework import serializers
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

class OpenAIClient:
    @staticmethod
    def generate_response(prompt: str) -> str:
        try:
            response = client.chat.completions.create(model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful wellness assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7)
            return response.choices[0].message.content
        except Exception as e:
            raise serializers.ValidationError(
                    {"message": f"Error: {str(e)}", "status":"failed"},
                    code=400
                )
