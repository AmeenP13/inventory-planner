import os
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
load_dotenv()


def is_dummy_key(key: str) -> bool:
    """Checks if the key is empty, too short, or matches placeholder patterns."""
    if not key:
        return True
    key = key.strip()
    if (
        "dummy" in key.lower() or
        "your_" in key.lower() or
        "placeholder" in key.lower() or
        "key_here" in key.lower() or
        key.startswith("AIzaSy...") or
        len(key) < 20
    ):
        return True
    return False


# Ensure we have a valid key, otherwise raise a hard exception immediately
current_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if is_dummy_key(current_key):
    raise ValueError(
        "Google Gemini API Key is not configured or is a dummy placeholder key. "
        "Please update the GEMINI_API_KEY value in your .env file with a valid API key."
    )

llm = init_chat_model(
    'gemini-2.5-flash',
    model_provider='google_genai'
)
