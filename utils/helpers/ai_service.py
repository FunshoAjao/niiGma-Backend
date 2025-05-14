import openai
from django.conf import settings

openai.api_key = settings.OPENAI_API_KEY

class OpenAIClient:
    @staticmethod
    def generate_response(prompt: str) -> str:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful wellness assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response['choices'][0]['message']['content']
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return f"Error: {str(e)}"
