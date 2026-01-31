from fpdf import FPDF
import os
import uuid
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from app.core.config import settings

class PDFService:
    def __init__(self):
        cloudinary.config( 
            cloud_name = settings.CLOUDINARY_CLOUD_NAME, 
            api_key = settings.CLOUDINARY_API_KEY, 
            api_secret = settings.CLOUDINARY_API_SECRET,
            secure = True
        )

    def sanitize_text(self, text: str) -> str:
        if not text: return ""
        replacements = {'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2013': '-'}
        for char, r in replacements.items():
            text = text.replace(char, r)
        return text.encode('latin-1', 'replace').decode('latin-1')

    def create_table_report(self, scenes: list, score: int, critique: list, project_name="Validated_Script") -> str:
        unique_id = uuid.uuid4().hex[:8]
        filename = f"audit_{project_name}_{unique_id}.pdf"
        
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # --- 1. HEADER & SCORECARD (RESTORED) ---
        # Blue Header Bar
        pdf.set_fill_color(20, 30, 70) 
        pdf.rect(0, 0, 210, 30, 'F')
        pdf.set_y(10)
        pdf.set_font("Arial", 'B', 22)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, f"Script Audit: {project_name[:20]}", ln=True, align='C')
        pdf.ln(25) 

        # Score & Critique Box
        start_y = pdf.get_y()
        pdf.set_fill_color(245, 247, 250) # Light Gray background
        pdf.rect(10, start_y, 190, 60, 'F')
        
        pdf.set_xy(15, start_y + 5)
        pdf.set_text_color(20, 30, 70)
        pdf.set_font("Arial", 'B', 26)
        pdf.cell(0, 15, f"Viral Score: {score}/100", ln=True)
        
        # Critique Bullet Points
        pdf.set_text_color(50, 50, 50)
        pdf.set_font("Arial", size=10)
        current_y = pdf.get_y()
        
        for point in critique[:4]: # Limit to 4 bullet points to fit box
            pdf.set_xy(15, current_y)
            pdf.multi_cell(180, 5, self.sanitize_text(f"• {point}"))
            current_y = pdf.get_y() + 2

        # Move cursor below the scorecard to start the table
        pdf.set_y(start_y + 70)

        # --- 2. TABLE HEADERS ---
        pdf.set_font("Arial", 'B', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(220, 220, 220)
        
        # Draw Headers
        pdf.cell(15, 10, "Sc#", 1, 0, 'C', True)
        pdf.cell(85, 10, "Visual Cue & AI Prompt", 1, 0, 'C', True)
        pdf.cell(90, 10, "Audio / Dialogue", 1, 1, 'C', True)
        
        # --- 3. TABLE BODY (GREEN EDITS LOGIC) ---
        pdf.set_font("Arial", '', 9)
        
        for scene in scenes:
            s_id = str(scene.get('scene_number', '?'))
            visual = self.sanitize_text(scene.get('visual_cue', ''))
            audio = self.sanitize_text(scene.get('audio_dialogue', ''))
            is_edited = scene.get('is_edited', False)

            # Calculate Row Height
            lines_visual = pdf.multi_cell(85, 5, visual, split_only=True)
            lines_audio = pdf.multi_cell(90, 5, audio, split_only=True)
            max_lines = max(len(lines_visual), len(lines_audio))
            row_height = max_lines * 5 
            
            # Page Break Check
            if pdf.get_y() + row_height > 270:
                pdf.add_page()
                # Re-draw headers on new page
                pdf.set_font("Arial", 'B', 10)
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(15, 10, "Sc#", 1, 0, 'C', True)
                pdf.cell(85, 10, "Visual Cue & AI Prompt", 1, 0, 'C', True)
                pdf.cell(90, 10, "Audio / Dialogue", 1, 1, 'C', True)
                pdf.set_font("Arial", '', 9)

            x_start = pdf.get_x()
            y_start = pdf.get_y()
            
            # Col 1: ID
            pdf.set_text_color(0, 0, 0)
            pdf.rect(x_start, y_start, 15, row_height)
            pdf.multi_cell(15, row_height, s_id, border=0, align='C')
            
            # Col 2: Visuals (Check Green)
            pdf.set_xy(x_start + 15, y_start)
            if is_edited: pdf.set_text_color(0, 128, 0) # Green
            else: pdf.set_text_color(0, 0, 0)
            
            pdf.rect(pdf.get_x(), y_start, 85, row_height)
            pdf.multi_cell(85, 5, visual, border=0)
            
            # Col 3: Audio (Check Green)
            pdf.set_xy(x_start + 100, y_start)
            if is_edited: pdf.set_text_color(0, 128, 0)
            else: pdf.set_text_color(0, 0, 0)
            
            pdf.rect(pdf.get_x(), y_start, 90, row_height)
            pdf.multi_cell(90, 5, audio, border=0)
            
            # Reset for next row
            pdf.set_xy(x_start, y_start + row_height)
            pdf.set_text_color(0, 0, 0)

        # --- 4. UPLOAD ---
        temp_path = f"temp_{filename}"
        pdf.output(temp_path)
        
        try:
            unique_id_cloudinary = filename.split('.')[0]
            cloudinary.uploader.upload(temp_path, public_id=f"scripts/{unique_id_cloudinary}", resource_type="image", format="pdf", overwrite=True)
            pdf_url, _ = cloudinary.utils.cloudinary_url(f"scripts/{unique_id_cloudinary}", resource_type="image", format="pdf")
            if os.path.exists(temp_path): os.remove(temp_path)
            return pdf_url
        except Exception:
            return "error_generating_pdf"