import json
import re
import google.generativeai as genai
from typing import List, Tuple
from app.core.config import settings
from app.schemas.script import Edit

class ScriptEditorService:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        genai.configure(api_key=settings.GEMINI_API_KEY)

    async def analyze_script(self, script: str, tone: str) -> Tuple[List[Edit], int, List[str]]:
        print(f"\n--- 🧠 STARTING RUTHLESS AUDIT FOR TONE: {tone.upper()} ---")
        
        # PROMPT: We explicitly tell it to capture UNIQUE short phrases to make matching easier
        prompt = f"""
        Act as a Ruthless YouTube Script Editor. 
        Target Tone: {tone}

        INSTRUCTIONS:
        1. Score the script (0-100) on Hooks, Retention, and Payoff.
        2. If score < 100, you MUST provide at least 3 edits.
        3. CRITICAL: When choosing "original_snippet", pick a unique 5-10 word phrase that exists EXACTLY in the text. Do not quote huge paragraphs.

        RETURN JSON ONLY:
        {{
            "final_score": 75,
            "critique": ["Hook is weak", "Pacing is slow"],
            "edits": [
                {{
                    "original_snippet": "existing text here",
                    "improved_snippet": "better text here",
                    "reason": "Fixing weak hook"
                }}
            ]
        }}

        SCRIPT:
        "{script[:25000]}"
        """
        
        try:
            response = self.model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            data = json.loads(response.text)
            
            final_score = data.get("final_score", 0)
            critique = data.get("critique", [])
            edits = [Edit(**item) for item in data.get("edits", []) if item.get("original_snippet")]
            
            print(f"--- 🧠 AUDIT COMPLETE: {final_score}/100 ---")
            print(f"--- Found {len(edits)} edits to apply ---")
            
            return edits, final_score, critique
            
        except Exception as e:
            print(f"❌ Analysis Error: {e}")
            return [], 0, ["Error: AI Analysis Failed"]

    def normalize_text(self, text: str) -> str:
        """Removes all whitespace/newlines to compare purely characters."""
        return re.sub(r'\s+', '', text).lower()

    def apply_patches(self, original_script: str, edits: List[Edit]) -> str:
        """
        Smart Patching: Replaces text even if whitespace/newlines don't match perfectly.
        """
        final_script = original_script
        
        for edit in edits:
            original_snippet = edit.original_snippet
            improved_snippet = edit.improved_snippet
            
            # 1. Try Exact Match (Fastest)
            if original_snippet in final_script:
                final_script = final_script.replace(original_snippet, improved_snippet, 1)
                continue
            
            # 2. Try "Flexible Whitespace" Match (Regex)
            # This turns "hello world" into "hello\s+world" to match newlines
            escaped_snippet = re.escape(original_snippet)
            # Replace escaped spaces with \s+ (match any space/newline)
            flexible_pattern = escaped_snippet.replace(r'\ ', r'\s+')
            
            match = re.search(flexible_pattern, final_script, re.IGNORECASE)
            if match:
                print(f"✅ Fuzzy Match Found: replaced '{original_snippet[:20]}...'")
                # We replace exactly what we found in the original text
                final_script = final_script[:match.start()] + improved_snippet + final_script[match.end():]
                continue

            # 3. Fallback: If AI Hallucinated slightly, we skip to avoid breaking the script
            print(f"⚠️ Failed to apply edit: '{original_snippet[:30]}...' (Text not found)")
            
        return final_script