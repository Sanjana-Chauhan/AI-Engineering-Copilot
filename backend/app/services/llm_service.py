import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)


def generate_response(message: str) -> str:

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=message
    )

    return response.text


def generate_response_stream(message: str):

    stream = client.models.generate_content_stream(
        model="gemini-3.6-flash",
        contents=message
    )

    for chunk in stream:
        if chunk.text:
            yield chunk.text