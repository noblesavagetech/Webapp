# AI summarization logic using OpenAI API
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def summarize_customer_info(info):
    if not OPENAI_API_KEY:
        return "No API key found."
    client = OpenAI(api_key=OPENAI_API_KEY)
    # Example prompt for summarization
    prompt = f"Summarize the following customer info: {info}"
    try:
        response = client.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=100
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"AI summarization error: {e}"
