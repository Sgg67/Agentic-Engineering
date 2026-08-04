import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
google_api_key = os.getenv("GEMINI_API_KEY")
gemini = OpenAI(base_url=GEMINI_BASE_URL, api_key=google_api_key)

# ask it what bussiness I can add agentic ai to
question = "Pick a bussiness area that might be worth exploring for an Agentic AI opportunity"
messages={"role":"user", "content": question}
response = gemini.chat.completions.create(model="gemini-3.5-flash", messages=messages)
industry = response.choices[0].message.content

print(industry)