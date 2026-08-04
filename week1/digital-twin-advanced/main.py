# import necessary dependencies
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from pypdf import PdfReader
from IPython.display import Markdown, display
import gradio as gr
import requests

# load env variables
load_dotenv()

# setup llm information
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
google_api_key = os.getenv("GEMINI_API_KEY")
gemini = OpenAI(base_url=GEMINI_BASE_URL, api_key=google_api_key)


# add pushover credentials
pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

def push(message):
    print(f"Push:{message}")
    payload = {"user": pushover_user, "token": pushover_token, "message": message}
    requests.post(pushover_url, data=payload)

def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording interest from {name} with email {email} and notes {notes}")
    return "OK"

def record_unknown_question(question):
    push(f"Recording {question} asked that I couldn't answer")
    return "OK"

# describes the user details
record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "The email address of this user"},
            "name": {"type": "string", "description": "The user's name, if they provided it"},
            "notes": {"type": "string", "description": "Any additional info about the conversation that's worth recording for context"}
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

# records any question that could not be answered
record_unknown_questions_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question that couldn't be answered"}
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

# convert the json to be a tool
tools = [
         {"type": "function", "function": record_user_details_json},
         {"type": "function", "function": record_unknown_questions_json}
        ]

# This function takes a list of tool calls, and run them
def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Tool called: {tool_name}", flush=True)

        if tool_name == "record_user_details":
            result = record_user_details(**arguments)
        elif tool_name == "record_unknown_question":
            result = record_unknown_question(**arguments)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        results.append({"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call.id})
    return results


# parse in the document information
reader = PdfReader("../Sage_Yanoff_Resume_v4.pdf")
resume = ""
for page in reader.pages:
    text = page.extract_text()
    if text:
        resume += text


# construct system prompt that gives context to the llm
system_prompt = f"""

You are a digital twin running on a website, chatting with visitors of the website.
You represent the person who's website you are on.
You answer questions related to their career, background, skills and experience.

Here are the details of the person you are representing:
{resume}

# Rules
Engage with the user. Be professional and engaging, as if talking to a potential client or future employer who came across the profile.
 Avoid answering questions that are not related to the user's career, background , skills and experience;
 steer the conversations back to professional topics.

 Always stay in character as the digital twin of the person you are representing. Represent the person.

 If the use would like to get in touch, then ask for their email, and use your tool to record their email for follow-up
 IMPORTANT: if you don't know the answer, use your toool to record the question, and then tell the user you don't know. Never make up an answer.
 If the user asks about something not in the context, say that you don't know.

"""

# set up user and system prompt and send a chat to llm and use history
def chat(message, history):
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]
    response = gemini.chat.completions.create(model="gemini-2.5-flash", messages=messages, tools=tools)

    while response.choices[0].finish_reason == "tool_calls":
        message = response.choices[0].message
        tool_calls = message.tool_calls
        results = handle_tool_calls(tool_calls)
        messages.append(message)
        messages.extend(results)
        response = gemini.chat.completions.create(model="gemini-2.5-flash", messages=messages, tools=tools)
    return response.choices[0].message.content

gr.ChatInterface(chat).launch(inbrowser=True)