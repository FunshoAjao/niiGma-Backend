from openai import OpenAI
from rest_framework import serializers
from django.conf import settings
import json
from rest_framework.exceptions import APIException

class VerificationFailed(APIException):
    status_code = 400
    default_detail = "Invalid or expired verification code"
    default_code = "verification_failed"

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
            
    @staticmethod
    def generate_response_list(prompt: str):
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

    @staticmethod
    def generate_daily_meal_plan(prompt):
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        try:
            content = response.choices[0].message.content
            return json.loads(content)
        except json.JSONDecodeError as e:
            print("⚠️ Failed to parse AI JSON:", e)
            print("Raw content:", content)
            return None
        except Exception as e:
            print("Error parsing meal plan:", e)
            return None
        
    @staticmethod
    def chat(prompt):
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    
    @staticmethod
    def chat_with_base64_image(base64_image: str, text: str = "", context: str = ""):
        try:
            messages = [
                {"role": "system", "content": f"You are a helpful fitness assistant. {context}"},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": base64_image  # Must start with data:image/jpeg;base64,...
                            }
                        },
                        {
                            "type": "text",
                            "text": text or "Please describe this meal or item."
                        }
                    ]
                }
            ]

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=800
            )

            return response.choices[0].message.content
        except Exception as e:
            raise VerificationFailed(f"{str(e)}")