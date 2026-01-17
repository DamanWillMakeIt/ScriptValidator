from pydantic import BaseModel, HttpUrl
from typing import List, Optional

# INPUT: What the user sends us
class ScriptRequest(BaseModel):
    # FIXED: Made 'content' optional so you can just send 'script_url' if you want
    content: Optional[str] = None 
    script_url: Optional[str] = None
    
    tone: str = "engaging" 
    topic: str = "General"
    fetch_competitors: bool = True

# OUTPUT: What we send back
class Edit(BaseModel):
    original_snippet: str
    improved_snippet: str
    reason: str

class AnalysisResult(BaseModel):
    score: int
    critique: List[str]

class ScriptResponse(BaseModel):
    analysis: AnalysisResult
    applied_edits: List[Edit]
    competitors: List[dict] = []
    final_script: str
    pdf_download_url: Optional[str] = None