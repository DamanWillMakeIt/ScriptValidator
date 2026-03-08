from fastapi import APIRouter, HTTPException
import traceback
from app.schemas.script import ScriptValidateRequest, ScriptValidateResponse, AnalysisResult
from app.services.editor import ScriptEditorService
from app.services.pdf_builder import PDFService

router = APIRouter()

editor_service = ScriptEditorService()
pdf_service = PDFService()


@router.post("/validate", response_model=ScriptValidateResponse)
async def validate_script(payload: ScriptValidateRequest):
    try:
        if not payload.scenes:
            raise HTTPException(status_code=400, detail="No scenes provided.")

        print(f"\n📋 [Validator] Received {len(payload.scenes)} scenes | Topic: {payload.topic}")

        # 1. Scene-aware AI analysis
        operations, score, critique = await editor_service.analyze_scenes(
            scenes=payload.scenes,
            tone=payload.tone,
            topic=payload.topic
        )

        # 2. Apply operations → build final scenes
        final_scenes = editor_service.apply_operations(
            original_scenes=payload.scenes,
            operations=operations
        )

        print(f"🏗️  [Validator] Final scene count: {len(final_scenes)} (was {len(payload.scenes)})")

        # 3. Build PDF
        print("📄 [Validator] Building audit PDF...")
        analysis = AnalysisResult(score=score, critique=critique)
        pdf_url = pdf_service.create_report(
            final_scenes=final_scenes,
            original_scenes=payload.scenes,
            operations=operations,
            analysis=analysis,
            project_name=payload.topic or "Script_Audit"
        )

        print(f"✅ [Validator] Done. PDF: {pdf_url}")

        return ScriptValidateResponse(
            analysis=analysis,
            operations=operations,
            final_scenes=[s.model_dump() for s in final_scenes],
            pdf_download_url=pdf_url
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
