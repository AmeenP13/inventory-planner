import os
from dotenv import load_dotenv
load_dotenv()
from google import genai

def main():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    print("Listing models:")
    try:
        response = client.models.list()
        for m in response:
            if "embed" in m.name.lower():
                print(f"Name: {m.name}, Supported Methods: {m.supported_actions}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
