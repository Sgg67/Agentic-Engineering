import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv(override=True)
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
google_api_key = os.getenv("GEMINI_API_KEY")
gemini = OpenAI(base_url=GEMINI_BASE_URL, api_key=google_api_key)

# ask it what bussiness I can add agentic ai to
question = "Pick a bussiness area that might be worth exploring for an Agentic AI opportunity"
messages={"role":"user", "content": question}
response = gemini.chat.completions.create(model="gemini-2.5-flash-lite", messages=messages)
industry = response.choices[0].message.content

# configure a message to ask ai which is a pain
# ask an llm if the response is correct
message = f"""
    Here is a an industry:
    {industry}

    Given the industry present a pain-point in that industry -
    that could possibly be solved with AI
"""
messages={"role":"user", "content": message}
response = gemini.chat.completions.create(model="gemini-2.5-flash-lite", messages=messages)
painpoint = response.choices[0].message.content

# ask the llm given the industry  and painpoint, what a possible agentic solution can be
message = f"""
    Here is a an industry:
    {industry}

    Given the industry and a possible painpoint in that industry
     {painpoint}, provide an agentic solution to that problem
"""

messages={"role":"user", "content": message}
response = gemini.chat.completions.create(model="gemini-2.5-flash", messages=messages)
solution = response.choices[0].message.content
print(solution)

