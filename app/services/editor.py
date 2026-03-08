import json
import re
import google.generativeai as genai
from typing import List, Tuple, Dict, Any
from app.core.config import settings
from app.schemas.script import ArchitectScene, FinalScene

class ScriptEditorService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    async def analyze_scenes(
        self,
        scenes: List[ArchitectScene],
        tone: str,
        topic: str
    ) -> Tuple[List[Dict], int, List[str]]:
        """
        Sends structured scenes to Gemini and returns scene-level operations.
        """
        print(f"\n--- 🧠 SCENE-AWARE AUDIT | Topic: {topic} | Tone: {tone.upper()} ---")

        scenes_json = json.dumps([
            {
                "scene_number": s.scene_number,
                "script_dialogue": s.script_dialogue,
                "veo_prompt": s.veo_prompt,
                "estimated_time_seconds": s.estimated_time_seconds,
            }
            for s in scenes
        ], indent=2)

        prompt = f"""
You are a ruthless YouTube script editor analyzing a structured scene-by-scene script.

Topic: {topic}
Target Tone: {tone}
Total Scenes: {len(scenes)}

YOUR TASK:
1. Score the script 0-100 on: Hook Strength, Pacing, Retention, CTA Quality.
2. Write 2-4 specific critique points (not generic — reference actual scene content).
3. Return scene-level operations to fix the script. Be surgical — only touch what genuinely needs it.
   If score >= 90, you may return fewer operations.
   If score < 90, return at least 3 meaningful operations.

AVAILABLE OPERATIONS:

"rewrite" — Improve a scene's dialogue and/or veo_prompt. Use when the content is salvageable but poorly executed.
"delete"  — Remove a scene entirely. Use for redundant, padding, or weak scenes.
"add"     — Insert a brand-new scene after a specific scene. Use only when there is a genuine structural gap (missing hook, missing transition, missing CTA).
"merge"   — Combine two adjacent weak scenes into one stronger scene.
"split"   — Break one overloaded scene (too many ideas) into two focused scenes.

RULES:
- Every operation must have a specific, concrete reason — no generic phrases like "improves flow".
- For "rewrite": keep the core message, improve the delivery. Preserve veo_prompt style.
- For "add": the new_dialogue and new_veo_prompt must match the topic and tone perfectly.
- For "merge": scene_numbers must be exactly 2 adjacent scenes (e.g. [3,4] not [1,5]).
- For "split": the two new scenes must together cover the original scene's content completely.

RETURN VALID JSON ONLY — no markdown, no explanation outside the JSON:

{{
  "score": <int>,
  "critique": ["<specific point referencing scene content>", ...],
  "operations": [
    {{
      "type": "rewrite",
      "scene_number": <int>,
      "reason": "<specific reason>",
      "updated_dialogue": "<improved dialogue>",
      "updated_veo_prompt": "<improved veo prompt>"
    }},
    {{
      "type": "delete",
      "scene_number": <int>,
      "reason": "<specific reason>"
    }},
    {{
      "type": "add",
      "after_scene_number": <int>,
      "reason": "<what gap this fills>",
      "new_dialogue": "<new scene dialogue>",
      "new_veo_prompt": "<new scene veo prompt>"
    }},
    {{
      "type": "merge",
      "scene_numbers": [<int>, <int>],
      "reason": "<specific reason>",
      "merged_dialogue": "<combined dialogue>",
      "merged_veo_prompt": "<combined veo prompt>"
    }},
    {{
      "type": "split",
      "scene_number": <int>,
      "reason": "<specific reason>",
      "new_scenes": [
        {{"dialogue": "<part A dialogue>", "veo_prompt": "<part A veo prompt>"}},
        {{"dialogue": "<part B dialogue>", "veo_prompt": "<part B veo prompt>"}}
      ]
    }}
  ]
}}

SCRIPT SCENES:
{scenes_json}
"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            raw = response.text.strip()

            # Strip markdown fences if Gemini adds them
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            data = json.loads(raw)

            score = int(data.get("score", 0))
            critique = data.get("critique", [])
            operations = data.get("operations", [])

            # Validate operation types
            valid_types = {"rewrite", "delete", "add", "merge", "split"}
            operations = [op for op in operations if op.get("type") in valid_types]

            print(f"--- 🧠 AUDIT COMPLETE: {score}/100 | {len(operations)} operations ---")
            return operations, score, critique

        except Exception as e:
            print(f"❌ Analysis Error: {e}")
            return [], 0, ["Error: AI analysis failed. Please try again."]

    def apply_operations(
        self,
        original_scenes: List[ArchitectScene],
        operations: List[Dict]
    ) -> List[FinalScene]:
        """
        Applies scene-level operations to produce the final scene list.
        Returns FinalScene objects with status annotations.
        """
        # Index original scenes by scene_number
        scene_map: Dict[int, ArchitectScene] = {s.scene_number: s for s in original_scenes}

        # Collect which scenes are deleted or consumed by merges
        deleted: set = set()
        merge_consumed: set = set()  # scenes merged INTO the first scene (removed)
        merge_ops: Dict[int, Dict] = {}  # first scene_number -> merge op
        rewrite_ops: Dict[int, Dict] = {}
        split_ops: Dict[int, Dict] = {}
        add_ops: Dict[int, Dict] = {}  # after_scene_number -> op

        for op in operations:
            t = op.get("type")
            if t == "delete":
                deleted.add(op["scene_number"])
            elif t == "merge":
                sns = op.get("scene_numbers", [])
                if len(sns) >= 2:
                    merge_ops[sns[0]] = op
                    for sn in sns[1:]:
                        merge_consumed.add(sn)
            elif t == "rewrite":
                rewrite_ops[op["scene_number"]] = op
            elif t == "split":
                split_ops[op["scene_number"]] = op
            elif t == "add":
                add_ops[op["after_scene_number"]] = op

        final: List[FinalScene] = []

        for scene in original_scenes:
            sn = scene.scene_number

            # Skip deleted and merge-consumed scenes
            if sn in deleted or sn in merge_consumed:
                continue

            if sn in split_ops:
                # Split: replace with 2 new scenes
                op = split_ops[sn]
                for ns in op.get("new_scenes", []):
                    final.append(FinalScene(
                        scene_number=0,  # renumbered below
                        script_dialogue=ns.get("dialogue", ""),
                        veo_prompt=ns.get("veo_prompt", ""),
                        status="split",
                        operation_reason=op.get("reason")
                    ))
            elif sn in merge_ops:
                # Merge: replace first scene with merged content
                op = merge_ops[sn]
                final.append(FinalScene(
                    scene_number=0,
                    script_dialogue=op.get("merged_dialogue", scene.script_dialogue),
                    veo_prompt=op.get("merged_veo_prompt", scene.veo_prompt),
                    status="merged",
                    operation_reason=op.get("reason")
                ))
            elif sn in rewrite_ops:
                # Rewrite: replace dialogue/veo_prompt
                op = rewrite_ops[sn]
                final.append(FinalScene(
                    scene_number=0,
                    script_dialogue=op.get("updated_dialogue", scene.script_dialogue),
                    veo_prompt=op.get("updated_veo_prompt", scene.veo_prompt),
                    status="rewritten",
                    operation_reason=op.get("reason")
                ))
            else:
                # Original: no operation
                final.append(FinalScene(
                    scene_number=0,
                    script_dialogue=scene.script_dialogue,
                    veo_prompt=scene.veo_prompt,
                    status="original"
                ))

            # Insert any "add" scene after this scene
            if sn in add_ops:
                op = add_ops[sn]
                final.append(FinalScene(
                    scene_number=0,
                    script_dialogue=op.get("new_dialogue", ""),
                    veo_prompt=op.get("new_veo_prompt", ""),
                    status="added",
                    operation_reason=op.get("reason")
                ))

        # Renumber sequentially
        for i, s in enumerate(final):
            s.scene_number = i + 1

        return final
