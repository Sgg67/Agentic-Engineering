import os
import asyncio
import smtplib
import requests
from email.message import EmailMessage
from typing import Dict

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent

# 1. FIXED: Removed OpenAIChatCompletionsModel from main agents import
from agents import Agent, Runner, set_tracing_export_api_key, trace, function_tool, ModelSettings

# 2. FIXED: Imported OpenAIChatCompletionsModel from its submodule
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from agents.extensions.visualization import draw_graph

load_dotenv()

set_tracing_export_api_key(os.getenv("OPENAI_API_KEY"))

gemini_client = AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

gemini_model = OpenAIChatCompletionsModel(
    openai_client=gemini_client,
    model="gemini-2.5-flash"
)

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER")

# 3. FIXED: Corrected spelling to match standard EMAIL_APP_PASSWORD
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

USE_EMAIL = EMAIL_ADDRESS and EMAIL_SMTP_SERVER and EMAIL_APP_PASSWORD

def send_email(subject, text_body, html_body):
    msg = EmailMessage()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(EMAIL_SMTP_SERVER, 587) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.send_message(msg)

pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

def push(message):
    print(f"Push: {message}")
    payload = {"user": pushover_user, "token": pushover_token, "message": message}
    requests.post(pushover_url, data=payload)

def send_message(subject, text_body, html_body):
    if USE_EMAIL:
        send_email(subject, text_body, html_body)
    else:
        push(f"Subject: {subject} \n\n{text_body}")


# orchestrating by code
intro = """
you are a sales agent working for ComplAI,
a company that provides a SaaS tool for ensuring SOC2 compliance and preparing for audits, powered by AI.
You write emails.
"""

instruction1 = intro + "Your email style is professional, serious, with gravitas and credibility."
instruction2 = intro + "your email style is witty, enganing, and humorous."
instruction3 = intro + "your email style is concise, to the point, in the style of a busy senior executive."

sales_agent1 = Agent(name="Professional Sales Agent", instructions=instruction1, model=gemini_model)
sales_agent2 = Agent(name="Humorous Sales Agent", instructions=instruction2, model=gemini_model)
sales_agent3 = Agent(name="Executive Sales Agent", instructions=instruction3, model=gemini_model)


async def cold_email():
    result = Runner.run_streamed(sales_agent1, input="Write a cold sales email")
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end="", flush = True)


async def cold_email_parallel():
    message = "Write a cold sales email"
    with trace("Parallel cold emails"):
        results = await asyncio.gather(
            Runner.run(sales_agent1, message),
            Runner.run(sales_agent2, message),
            Runner.run(sales_agent3, message),
        )
    outputs = [result.final_output for result in results]

    for output in outputs:
        print(output + "\n\n")


decision = """
You pick the best cold sales email from the given options.
Imagine you are a customer and pick the one you are most likely to respond to.
Do not give an explanation; reply with the selected email only.
"""

sales_picker = Agent(name="Sales_picker", instructions=decision, model=gemini_model)

message = "Write a cold sales email"

async def selection_workflow():
    with trace("Sales selection workflow"):
        results = await asyncio.gather(
            Runner.run(sales_agent1, message),
            Runner.run(sales_agent2, message),
            Runner.run(sales_agent3, message),
        )
        outputs = [result.final_output for result in results]
        emails = "Cold sales emails: \n\n" + "\n\nEmail:\n\n".join(outputs)
        best = await Runner.run(sales_picker, emails)
        print(f"Best sales email:\n{best.final_output}")

# add a tool to the mix
@function_tool
def send_email_tool(subject:str, text_body:str, html_body: str) -> str:
    """
    Send out an email with the given subject and body to all sales prospects

    Args:
        subject: The subject of the email
        text_body: The body of the email as plain text
        html_body: The HTML body of the email
    """

    send_email(subject, text_body, html_body)
    return "Email sent succesfully"

decision = """
You pick the best cold sales email from the given options.
Imagine you are a customer and pick the one you are most likely to respond to.
Then use your tool to send the email.
"""

require_tool = ModelSettings(tool_choice="required")

sales_sender = Agent(name="Sales sender", instructions=decision, model=gemini_model, tools=[send_email_tool], model_settings=require_tool)

async def sales_agent_with_tools():
    message = "write a cold sales email"

    with trace("Sales selection workflow with sending"):
        results = await asyncio.gather(
            Runner.run(sales_agent1, message),
            Runner.run(sales_agent2, message),
            Runner.run(sales_agent3, message)
        )

        outputs = [result.final_output for result in results]

        emails = "Cold sales email:\n\n" + "\n\nEmail:\n\n".join(outputs)

        response = await Runner.run(sales_sender, emails)

        print(f"Final Response:\n{response.final_output}")


description = "Use this tool to write a sales email. In the input, just instruct it to write a sales email."

tool1 = sales_agent1.as_tool(tool_name="sales_email_writer_1", tool_description=description)
tool2 = sales_agent1.as_tool(tool_name="sales_email_writer_2", tool_description=description)
tool3 = sales_agent1.as_tool(tool_name="sales_email_writer_3", tool_description=description)

tools = [tool1,tool2,tool3]
instructions = """
You are a Sales Manager at ComplAI. Your goal is to find the single best cold sales email using the sales_writer tools.
"""

task = """
Follow these steps:

1. Generate Drafts: Use each of the three sales_email_writer tools to generate different email drafts.
Just instruct each to write a sales email; no further details are needed.
Do not proceed until all three drafts are ready, one from each tool.

2. Evaluate and Select: Review the drafts and choose the single best email using your judgement of which one is the most effective.

3. Use your tool to send the best email (and only the best email) to the user. Only send 1 email.
"""

sales_manager = Agent(name="Sales Manager", instructions=instructions, tools=tools, model=gemini_model)


# sales manager function
async def sales_agent():
    with trace("Sales manager"):
        result = await Runner.run(sales_manager, task)
        return result


# calling agents with handoffs
instructions = """
You are a sales manager at ComplAI. You get your sales team to draft emails, then send them all to a sales picker.
"""

task = """
follow these steps:

1. Generate Drafts: use each of the three sales_sales_email_writer tools to generate different email drafts.
Just instruct each to write a sales email; no further details are needed.
Do not proceed until all three drafts are ready, one from each tool.

2. Handoff to the sales sender to choose and send the best email
"""

tools = [tool1, tool2, tool3]
handoffs = [sales_sender]

sales_manager = Agent(name="Sales Manager", instructions=instructions, tools=tools, handoffs=handoffs, model=gemini_model)

draw_graph(sales_manager)

async def sales_manager_handoff():
    with trace("Sales manager"):
        result = await Runner.run(sales_manager, task)
    return result

response = asyncio.run(sales_manager_handoff())
print(response.final_output)