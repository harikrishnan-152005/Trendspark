# app/services/model_manager.py

import os
import time
import requests
from google import genai
from dotenv import load_dotenv

load_dotenv()

# -------------------------------------------------
# ENV VARIABLES
# -------------------------------------------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY missing in .env")

# Create Gemini client (NEW SDK)
client = genai.Client(api_key=GOOGLE_API_KEY)

_current_model_name = "gemini-2.5-flash"


# -------------------------------------------------
# GEMINI CALL WITH RETRY (NEW SDK)
# -------------------------------------------------
def _call_gemini(prompt: str):

    retries = 3
    delay = 1

    for attempt in range(retries):
        try:
            print(f"🤖 Gemini attempt {attempt + 1}")

            response = client.models.generate_content(
                model=_current_model_name,
                contents=prompt,
            )

            if response.text:
                return response.text

        except Exception as e:
            error_msg = str(e).lower()

            if "429" in error_msg or "quota" in error_msg:
                print("⚠️ Gemini quota hit. Retrying...")
                time.sleep(delay)
                delay *= 2
                continue

            print("❌ Gemini error:", e)
            break

    return None


# -------------------------------------------------
# OPENROUTER FALLBACK
# -------------------------------------------------
def _call_openrouter(prompt: str):

    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY missing")
        return None

    print("🔁 Switching to OpenRouter fallback...")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            print("❌ OpenRouter HTTP error:", response.status_code)
            print(response.text)
            return None

        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]

        print("❌ Unexpected OpenRouter response:", result)
        return None

    except Exception as e:
        print("❌ OpenRouter failure:", e)
        return None


# -------------------------------------------------
# MAIN AI ENTRY POINT
# -------------------------------------------------
def generate_ai(prompt: str):
    """
    Central AI generation function.
    Tries Gemini → fallback to OpenRouter.
    """

    gemini_result = _call_gemini(prompt)
    if gemini_result:
        return gemini_result

    openrouter_result = _call_openrouter(prompt)
    if openrouter_result:
        return openrouter_result

    print("❌ All AI providers failed")
    return None


# -------------------------------------------------
# OPTIONAL UTILITY
# -------------------------------------------------
def get_model_name():
    return _current_model_name