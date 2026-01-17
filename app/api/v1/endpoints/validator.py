from fastapi import APIRouter, HTTPException
from app.schemas.script import ScriptRequest, ScriptResponse, AnalysisResult
from app.services.editor import ScriptEditorService
from app.services.pdf_builder import PDFService
from app.services.researcher import ResearchService
from app.services.pdf_reader import PDFReaderService # <--- Import the new service

router = APIRouter()
editor_service = ScriptEditorService()
pdf_service = PDFService()
research_service = ResearchService()
reader_service = PDFReaderService() # <--- Initialize it

@router.post("/validate", response_model=ScriptResponse)
async def validate_script(payload: ScriptRequest):
    # --- 1. DETERMINE SOURCE (Text vs URL) ---
    script_content = ""

    if payload.script_url:
        # A. Download from URL
        script_content = await reader_service.download_and_parse(payload.script_url)
        
        # Log what we found for debugging
        print("\n🔍 SOURCE CHECK (URL Mode):")
        print(f"   • URL: {payload.script_url}")
        print(f"   • Length: {len(script_content)} chars")
        if len(script_content) > 0:
            print(f"   • Snippet: \"{script_content[:100]}...\"")
        print("-" * 30)
        
    elif payload.content:
        # B. Direct Text
        script_content = payload.content
    else:
        raise HTTPException(status_code=400, detail="You must provide either 'content' or 'script_url'")

    # Validate we actually got text
    if not script_content or len(script_content) < 10:
        raise HTTPException(status_code=400, detail="Could not extract valid text from the URL or input.")

    # --- 2. ANALYZE ---
    edits, score, critique = await editor_service.analyze_script(script_content, payload.tone)
    
    # --- 3. RESEARCH ---
    competitors = []
    if payload.fetch_competitors:
        competitors = research_service.search_videos(payload.topic)

    # --- 4. APPLY EDITS ---
    final_script = editor_service.apply_patches(script_content, edits)
    
    # --- 5. LOGS ---
    initial_wc = len(script_content.split())
    final_wc = len(final_script.split())
    
    # --- 6. GENERATE REPORT ---
    pdf_url = pdf_service.create_report(
        script=final_script, 
        edits=edits, 
        score=score, 
        critique=critique
    )
    
    print(f"\n📝 VALIDATION COMPLETE:")
    print(f"   • Score:      {score}/100")
    print(f"   • Words:      {initial_wc} -> {final_wc}")
    print(f"   • 🔗 Report:  {pdf_url}")
    print("-" * 40)

    analysis = AnalysisResult(score=score, critique=critique)

    return ScriptResponse(
        analysis=analysis,
        applied_edits=edits,
        competitors=competitors,
        final_script=final_script,
        pdf_download_url=pdf_url
    )