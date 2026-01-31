import re

class ScriptParser:
    def parse_text_to_scenes(self, raw_text: str) -> list:
        """
        Attempts to reconstruct the table structure from raw PDF text.
        Returns a list of dicts: [{'id': 1, 'visual': '...', 'audio': '...'}]
        """
        scenes = []
        
        # This regex looks for the pattern: 
        # "1" (Scene ID) -> followed by text -> followed by "? VEO PROMPT" (Visuals) -> followed by text (Audio)
        # It relies on your specific format "Visual Cue & AI Prompt" vs "Audio / Dialogue"
        
        # Heuristic: Split by Scene Numbers (e.g., "1", "2", "3" at start of lines)
        # Note: This is a "best effort" parser for raw text.
        
        # Split text by lines that look like just a number "1", "2"
        # pattern = r"\n(\d+)\n" 
        # This is tricky with raw PDF text. 
        # A safer bet for now is to ask Gemini to restructure it, 
        # but let's try a regex for your specific table layout.
        
        # Assuming the standard format you showed:
        matches = re.split(r'\n(\d+)\s+(?=[A-Z])', raw_text)
        
        if len(matches) < 2:
            # Fallback: Treat whole thing as Scene 1 if parsing fails
            return [{'id': 1, 'visual': 'Could not parse columns', 'audio': raw_text}]

        # Skip index 0 if it's header junk
        current_id = 1
        for i in range(1, len(matches), 2):
            scene_num = matches[i]
            content = matches[i+1] if i+1 < len(matches) else ""
            
            # Heuristic to split Visual vs Audio
            # We look for the "? VEO PROMPT" tag which is always in the visual column
            parts = content.split("? VEO PROMPT:")
            
            visual = ""
            audio = ""
            
            if len(parts) > 1:
                # The part BEFORE 'VEO PROMPT' is the visual cue description
                # The part AFTER includes the prompt AND likely the audio dialogue
                # This is hard to separate perfectly without OCR, but let's try:
                
                visual_part = parts[0].strip() + "\n\n? VEO PROMPT: " + parts[1].split('\n\n')[0]
                
                # Assume everything else is audio
                # This is messy. A better way: The Validator AI will fix the split.
                audio_part = parts[1].split('\n\n')[-1] # Last paragraph is usually audio
                
                visual = visual_part
                audio = audio_part
            else:
                visual = "Parsed content"
                audio = content
            
            scenes.append({
                "id": scene_num,
                "visual": visual,
                "audio": audio
            })
            
        return scenes