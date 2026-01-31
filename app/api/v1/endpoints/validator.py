from fastapi import APIRouter, HTTPException
import traceback
from app.schemas.script import ScriptRequest, ScriptResponse, AnalysisResult
from app.services.editor import ScriptEditorService
from app.services.pdf_builder import PDFService
from app.services.researcher import ResearchService
from app.services.pdf_reader import PDFReaderService
from app.services.ai_parser import AIParserService

router = APIRouter()

# Initialize Services
editor_service = ScriptEditorService()
pdf_service = PDFService()
research_service = ResearchService()
reader_service = PDFReaderService()
parser_service = AIParserService()

@router.post("/validate", response_model=ScriptResponse)
async def validate_script(payload: ScriptRequest):
    try:
        # --- 1. GET RAW TEXT ---
        script_content = ""
        if payload.script_url:
            print(f"📥 [Validator] Downloading PDF: {payload.script_url}")
            script_content = await reader_service.download_and_parse(payload.script_url)
        elif payload.content:
            script_content = payload.content
            
        if not script_content:
            raise HTTPException(status_code=400, detail="No text found in input.")

        # --- 2. GET INTELLIGENT EDITS ---
        print("🤖 [Validator] Agent is auditing the script...")
        edits, score, critique = await editor_service.analyze_script(script_content, payload.tone)
        
        # --- 3. APPLY EDITS TO TEXT ---
        # The Fuzzy Logic in Editor Service will now find and replace the text
        final_script_flat = editor_service.apply_patches(script_content, edits)
        
        # --- 4. RECONSTRUCT THE TABLE ---
        print("🏗️  [Validator] Reconstructing original table format...")
        scenes = parser_service.parse_messy_text_to_json(final_script_flat)
        
        # --- 5. GREEN HIGHLIGHT LOGIC ---
        print(f"🎨 [Validator] Highlighting {len(edits)} edits...")
        for scene in scenes:
            scene['is_edited'] = False
            # Flatten scene text to search for edits
            row_text = (str(scene.get('visual_cue', '')) + " " + str(scene.get('audio_dialogue', ''))).lower()
            
            for edit in edits:
                # Normalize the improved snippet for matching
                snippet = edit.improved_snippet.strip().lower()
                # If we find the improved text in this row, Mark it Green!
                if len(snippet) > 5 and snippet in row_text:
                    scene['is_edited'] = True
                    break

        # --- 6. PRINT THE PDF ---
        print("📄 [Validator] Printing Final PDF...")
        # We pass score & critique so they appear at the top of the PDF
        pdf_url = pdf_service.create_table_report(
            scenes=scenes,
            score=score,
            critique=critique,
            project_name=payload.topic or "Validated_Script"
        )
        
        print(f"✅ [Validator] Done! URL: {pdf_url}")

        # --- 7. RETURN CLEAN RESPONSE ---
        return ScriptResponse(
            analysis=AnalysisResult(score=score, critique=critique),
            applied_edits=edits,
            competitors=[],
            # IMPORTANT: We send empty string here so your JSON response isn't huge.
            # The full script is already inside the PDF URL.
            final_script="", 
            pdf_download_url=pdf_url
        )

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))