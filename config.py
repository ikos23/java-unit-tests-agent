import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# How many times the generator→validator loop will retry on test failure
MAX_RETRIES = 3

# Safety cap for the Analyzer's ReAct tool-calling loop
MAX_ANALYZER_TOOL_LOOPS = 10

if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY is not set.\n"
        "Copy .env.example to .env and add your OpenAI API key."
    )
