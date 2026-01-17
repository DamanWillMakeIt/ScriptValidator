from fpdf import FPDF
import os
import uuid
import re
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

    def format_script_text(self, text: str) -> str:
        """
        Smartly reformats a wall of text into paragraphs.
        """
        # 1. Un-escape literal newlines if present
        text = text.replace('\\n', '\n')
        
        # 2. If text already has paragraphs (more than 2 newlines), trust it.
        if text.count('\n') > 2:
            return text

        # 3. If it's a "Wall of Text", split by sentences
        # Split by . ! ? followed by a space
        sentences = re.split(r'(?<=[.!?]) +', text)
        
        paragraphs = []
        current_para = []
        
        # Group ~3 sentences per paragraph
        for i, sentence in enumerate(sentences):
            current_para.append(sentence)
            if (i + 1) % 3 == 0:
                paragraphs.append(" ".join(current_para))
                current_para = []
        
        # Add leftovers
        if current_para:
            paragraphs.append(" ".join(current_para))
            
        return "\n\n".join(paragraphs)

    def create_report(self, script: str, edits: list, score: int, critique: list) -> str:
        unique_id = uuid.uuid4().hex[:8]
        filename = f"script_audit_{unique_id}.pdf"

        pdf = FPDF()
        pdf.add_page()
        
        # --- HEADER ---
        pdf.set_fill_color(20, 30, 70) 
        pdf.rect(0, 0, 210, 30, 'F')
        pdf.set_y(10)
        pdf.set_font("Arial", 'B', 22)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, "YouTube Script Audit", ln=True, align='C')
        pdf.ln(25) 

        # --- SCORECARD ---
        start_y = pdf.get_y()
        pdf.set_fill_color(245, 247, 250)
        pdf.rect(10, start_y, 190, 75, 'F')
        
        pdf.set_xy(15, start_y + 5)
        pdf.set_text_color(20, 30, 70)
        pdf.set_font("Arial", 'B', 26)
        pdf.cell(0, 15, f"Viral Score: {score}/100", ln=True)
        
        pdf.set_text_color(50, 50, 50)
        current_y = pdf.get_y()
        
        for point in critique[:3]:
            pdf.set_xy(15, current_y)
            if ":" in point:
                title, text = point.split(":", 1)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 6, title + ":", ln=True)
                pdf.set_x(18)
                pdf.set_font("Arial", size=10)
                pdf.multi_cell(175, 5, text.strip())
                current_y = pdf.get_y() + 3
            else:
                pdf.set_font("Arial", size=10)
                pdf.multi_cell(180, 5, point)
                current_y = pdf.get_y() + 3

        pdf.set_y(start_y + 85)
        
        # --- IMPROVEMENTS ---
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(20, 30, 70)
        pdf.cell(0, 10, "Suggested Improvements", ln=True)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        if not edits:
            pdf.set_font("Arial", size=11)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 10, "No major issues found. Great job!", ln=True)

        for i, edit in enumerate(edits):
            pdf.set_font("Arial", 'B', 11)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 8, f"{i+1}. {edit.reason}", ln=True)
            pdf.set_font("Courier", size=10) 
            pdf.set_text_color(180, 0, 0)
            pdf.multi_cell(0, 5, f"[-] {edit.original_snippet}")
            pdf.set_text_color(0, 120, 0)
            pdf.multi_cell(0, 5, f"[+] {edit.improved_snippet}")
            pdf.ln(6) 

        pdf.add_page() 

        # --- FINAL SCRIPT DESIGN ---
        pdf.set_fill_color(20, 30, 70)
        pdf.rect(0, 0, 210, 20, 'F')
        pdf.set_y(5)
        pdf.set_font("Courier", 'B', 14) 
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, "FINAL OPTIMIZED SCRIPT", ln=True, align='C')
        pdf.ln(15)
        
        pdf.set_text_color(10, 10, 10)
        pdf.set_font("Courier", size=11) 
        
        # --- SMART FORMATTING APPLIED HERE ---
        formatted_script = self.format_script_text(script)
        
        # Split by DOUBLE newlines to get the paragraph blocks
        paragraphs = formatted_script.split('\n\n')
        
        for para in paragraphs:
            para = para.strip()
            if not para: 
                continue 
            
            # Sidebar Line
            start_y = pdf.get_y()
            pdf.set_draw_color(200, 200, 200)
            pdf.set_line_width(0.5)
            # Draw line relative to paragraph height
            # We don't know exact height yet, so we draw a fixed marker
            pdf.line(12, start_y, 12, start_y + 6) 
            
            pdf.set_x(15) 
            pdf.multi_cell(0, 6, para)
            
            # Gap between sections
            pdf.ln(6) 
        
        # --- UPLOAD ---
        temp_path = f"temp_{filename}"
        pdf.output(temp_path)
        
        try:
            print(f"☁️ Uploading {filename}...")
            unique_id_cloudinary = filename.split('.')[0]
            
            upload_result = cloudinary.uploader.upload(
                temp_path, 
                resource_type="image", 
                public_id=f"scripts/{unique_id_cloudinary}", 
                format="pdf",
                type="authenticated",
                overwrite=True
            )
            
            pdf_url, options = cloudinary.utils.cloudinary_url(
                f"scripts/{unique_id_cloudinary}",
                resource_type="image",
                type="authenticated",
                format="pdf",
                sign_url=True
            )
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return pdf_url
            
        except Exception as e:
            print(f"❌ Cloudinary Error: {e}")
            return f"http://127.0.0.1:8000/static/{filename}"