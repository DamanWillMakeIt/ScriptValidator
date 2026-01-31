import google.generativeai as genai
import json
import os
import re

class AIParserService:
    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def parse_messy_text_to_json(self, messy_text: str) -> list:
        """
        Takes raw script text and reconstructs the exact Table JSON 
        required by the PDF Builder.
        """
        prompt = f"""
        I have a YouTube script that lost its table formatting. 
        Please reconstruct it into a list of scenes so I can print it as a table again.

        RULES:
        1. "Visual Cue" column usually contains "VEO PROMPT".
        2. "Audio/Dialogue" column contains the spoken words.
        3. Keep the exact text content, just structure it.

        OUTPUT JSON FORMAT:
        [
            {{
                "scene_number": 1,
                "visual_cue": "Full visual description...",
                "audio_dialogue": "Spoken text..."
            }}
        ]

        RAW INPUT TEXT:
        {messy_text[:20000]} 
        """
        
        try:
            response = self.model.generate_content(prompt)
            clean_json = response.text.strip()
            
            # Clean up markdown if Gemini adds it
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0]
            elif "```" in clean_json:
                clean_json = clean_json.split("```")[1].split("```")[0]
                
            return json.loads(clean_json)
            
        except Exception as e:
            print(f"❌ Table Reconstruction Failed: {e}")
            # Fallback: Return text as one big row so data isn't lost
            return [{
                "scene_number": 1, 
                "visual_cue": "Error parsing table format.", 
                "audio_dialogue": messy_text[:1000]
            }]