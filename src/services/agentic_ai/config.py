import os
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
load_dotenv()

if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GEMINI_API_KEY"] = "dummy_key_to_prevent_import_crash"

llm=init_chat_model(
    'gemini-2.5-flash',
    model_provider='google_genai'
)