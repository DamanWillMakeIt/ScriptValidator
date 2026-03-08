from pydantic import BaseModel
from typing import List, Optional, Literal

# ── INPUT ────────────────────────────────────────────────────────────────────

class ArchitectScene(BaseModel):
    scene_number: int
    script_dialogue: str
    veo_prompt: str
    shoot_instructions: Optional[str] = ""
    estimated_time_seconds: Optional[int] = 0
    color_code: Optional[str] = "blue"

class ScriptValidateRequest(BaseModel):
    scenes: List[ArchitectScene]
    tone: str = "professional"
    topic: str = "General"

# ── OPERATIONS (returned to frontend as raw dicts) ───────────────────────────

# ── OUTPUT ───────────────────────────────────────────────────────────────────

class AnalysisResult(BaseModel):
    score: int
    critique: List[str]

class FinalScene(BaseModel):
    scene_number: int
    script_dialogue: str
    veo_prompt: str
    status: str  # "original" | "rewritten" | "added" | "merged" | "split"
    operation_reason: Optional[str] = None

class ScriptValidateResponse(BaseModel):
    analysis: AnalysisResult
    operations: List[dict]       # raw dicts so frontend can type-check freely
    final_scenes: List[FinalScene]
    pdf_download_url: Optional[str] = None
