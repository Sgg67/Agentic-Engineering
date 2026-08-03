import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv(override=True)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
question = "Please propose a hard challenging question to assess someone's IQ. Respond only with the question."
messages={"role":"user", "content": question}
google_api_key = os.getenv("GEMINI_API_KEY")
gemini = OpenAI(base_url=GEMINI_BASE_URL, api_key=google_api_key)
response = gemini.chat.completions.create(model="gemini-2.5-flash-lite", messages=messages)
question = response.choices[0].message.content

# ask the model the question it generated before
messages = {"role": "user", "content": question}
response = gemini.chat.completions.create(model="gemini-2.5-flash-lite", messages=messages)
answer = response.choices[0].message.content

# ask an llm if the response is correct
message = f"""
Here is a question:
{question}

And here is a possible answer that might be correct or incorrect:
{answer}

Please evaluate if the answer is correct or incorrect
"""
# check to see if response the llm gives is right
messages = {"role": "user", "content": message}
response = gemini.chat.completions.create(model="gemini-2.5-flash-lite", messages=messages)
second_answer = response.choices[0].message.content
print(second_answer)

