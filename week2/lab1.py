# import necessary dependencies
import os
from openai import AsyncOpenAI, OpenAI
import requests
import asyncio
from dotenv import load_dotenv
from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, Runner, set_tracing_disabled, set_tracing_export_api_key, trace, function_tool, SQLiteSession
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

# load env variables
load_dotenv()

set_tracing_export_api_key(os.getenv("OPENAI_API_KEY"))

# 2. Directly create the client using your GEMINI_API_KEY from .env
gemini_client = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# 3. Pass the client to the model adapter
gemini_model = OpenAIChatCompletionsModel(
    openai_client=gemini_client,
    model="gemini-2.5-flash"
)

# 4. Pass gemini_model directly to the Agent
agent = Agent[any](
    name="jokester", 
    instructions="you are a joke teller", 
    model=gemini_model
)
async def result():
    with trace("Telling a joke"):
        result = await Runner.run(agent, "Tell a joke about Autonomous AI Agents")
    return result

async def streamed():
    result = Runner.run_streamed(agent, input="Please tell me 5 jokes about AI Agents.")
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end="", flush=True)

pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

def push(message):
    print(f"Push: {message}")
    payload = {"user": pushover_user, "token": pushover_token, "message": message}
    requests.post(pushover_url, data=payload)


@function_tool
def push_tool(message: str) -> str:
    """Send the given message to the user as a push notification"""
    payload = {"user": pushover_user, "token": pushover_token, "message":message}
    result = requests.post(pushover_url, data=payload).status_code
    return f"Push sent with API status code {result}"

notifier = Agent[any](
    name="Notifier", 
    instructions="You notify the user when requested", 
    model=gemini_model,
    tools=[push_tool]
)

async def notifier_agent():
    with trace("Notifying the user"):
        result = await Runner.run(notifier, "Notify the user that the pizza is here")
    return result

agent = Agent[any](
    name="Assistant", 
    model=gemini_model,
)

async def memory():
    response = await Runner.run(agent, "Hi there. My name is Sage")
    response.to_input_list()
    next_input = response.to_input_list() + [{"role": "user", "content": "What's my name?"}]
    response = await Runner.run(agent, next_input)
    return response

async def db_memory():
    session = SQLiteSession("12345")
    response = await Runner.run(agent, "Hi there. My name is Sage.", session=session)
    answer = await Runner.run(agent, "What's my name?", session=session)
    return answer




