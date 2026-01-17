import google.generativeai as genai
import os
from dotenv import load_dotenv

# 1. Load your API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: GEMINI_API_KEY not found in .env file")
    exit()

# 2. Configure Gemini
genai.configure(api_key=api_key)

print(f"Checking models for key: {api_key[:5]}...********")

try:
    # 3. List all models
    print("\n--- AVAILABLE MODELS ---")
    found_any = False
    for m in genai.list_models():
        # Only show models that can generate text
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ {m.name}")
            found_any = True
    
    if not found_any:
        print("⚠️ No content generation models found. Your key might have restricted access.")

except Exception as e:
    print(f"❌ Error fetching models: {e}")