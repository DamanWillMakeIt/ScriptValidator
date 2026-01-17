import json
import google.generativeai as genai
from typing import List, Tuple
from app.core.config import settings
from app.schemas.script import Edit

class ScriptEditorService:
    def __init__(self):
        # Using the smartest model available to you
        self.model = genai.GenerativeModel('models/gemini-2.0-flash')
        genai.configure(api_key=settings.GEMINI_API_KEY)

    async def analyze_script(self, script: str, tone: str) -> Tuple[List[Edit], int, List[str]]:
        """
        Performs a component-based audit to generate a REAL score.
        """
        print(f"\n--- 🧠 STARTING INTELLIGENT AUDIT FOR TONE: {tone.upper()} ---")
        
        prompt = f"""
        Act as an expert YouTube Algorithm Analyst.
        Your job is to mathematically grade this script based on 3 pillars.
        Target Tone: {tone}

        --- SCORING FORMULA (Must equal 100) ---
        1. HOOK (0-35 pts): Does the first 30s grab attention immediately? Or is there "hello welcome back" fluff?
        2. RETENTION & PACING (0-35 pts): Are paragraphs short? Is there "slippery slope" writing?
        3. VIRALITY & PAYOFF (0-30 pts): Is the value clear? Is the CTA strong?

        Task:
        1. Calculate the score for each pillar strictly.
        2. Sum them for the Final Score.
        3. Provide a critique that specifically references these 3 scores.
        4. Find 3-5 actual weak sentences that hurt the score and rewrite them to fix the specific flaw.

        RETURN JSON ONLY:
        {{
            "hook_score": 20,
            "retention_score": 25,
            "virality_score": 20,
            "final_score": 65,
            "critique": [
                "Hook Score (20/35): Too slow. You wasted 10 seconds on intros.",
                "Retention (25/35): Good, but paragraph 3 is a wall of text.",
                "Virality (20/30): Strong ending, but needs a clearer ask."
            ],
            "edits": [
                {{
                    "original_snippet": "Hello guys welcome back to the channel today we talk about...",
                    "improved_snippet": "This specific strategy doubled my income in 2 weeks. Here is how.",
                    "reason": "Fixing Weak Hook: Removed fluff, started with immediate value."
                }}
            ]
        }}

        Script:
        "{script[:20000]}"
        """
        
        try:
            response = self.model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            data = json.loads(response.text)
            
            # 1. Get the Calculated Score
            final_score = data.get("final_score", 0)
            
            # 2. Get the Breakdown
            critique = data.get("critique", [])
            
            # 3. Get Edits
            edits = [Edit(**item) for item in data.get("edits", [])]
            
            print(f"--- 🧠 AUDIT COMPLETE: {final_score}/100 ---")
            print(f"--- Breakdown: {critique} ---")
            
            return edits, final_score, critique
            
        except Exception as e:
            print(f"❌ Analysis Error: {e}")
            return [], 0, ["Error: AI Analysis Failed"]

    def apply_patches(self, original_script: str, edits: List[Edit]) -> str:
        """
        Applies changes safely.
        """
        patched_script = original_script
        for edit in edits:
            # Normalize strings to avoid mismatch due to hidden spaces
            clean_orig = edit.original_snippet.strip()
            
            if clean_orig in patched_script:
                patched_script = patched_script.replace(clean_orig, edit.improved_snippet, 1)
            else:
                # If exact match fails, try a looser match (removing newlines)
                flat_orig = clean_orig.replace('\n', ' ')
                flat_script = patched_script.replace('\n', ' ')
                if flat_orig in flat_script:
                     # This is a bit complex to patch perfectly without regex, 
                     # but we return the unpatched version rather than breaking it.
                     pass 
        return patched_script