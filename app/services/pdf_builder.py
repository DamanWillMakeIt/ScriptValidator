from fpdf import FPDF, XPos, YPos
import os
import uuid
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from app.core.config import settings
from app.schemas.script import FinalScene, AnalysisResult

# ── STATUS COLOURS ─────────────────────────────────────────────────────────
STATUS_COLORS = {
    "rewritten": (255, 249, 219),   # soft amber
    "added":     (219, 244, 230),   # soft green
    "merged":    (219, 234, 255),   # soft blue
    "split":     (240, 224, 255),   # soft purple
    "original":  (255, 255, 255),   # white
}
STATUS_ACCENT = {
    "rewritten": (180, 120, 0),
    "added":     (20, 140, 60),
    "merged":    (20, 80, 180),
    "split":     (120, 40, 200),
    "original":  (100, 100, 100),
}
STATUS_LABEL = {
    "rewritten": "REWRITTEN",
    "added":     "NEW SCENE",
    "merged":    "MERGED",
    "split":     "SPLIT",
    "original":  "",
}

NAVY   = (15, 25, 65)
WHITE  = (255, 255, 255)
LIGHT  = (245, 247, 250)
MID    = (120, 130, 150)
DARK   = (30, 35, 50)


class PDFService:
    def __init__(self):
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )

    def sanitize(self, text: str) -> str:
        if not text:
            return ""
        replacements = {
            "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
            "\u2013": "-", "\u2014": "-", "\u2015": "-", "\u2026": "...",
            "\u00b7": "*", "\u2022": "*", "\u00e2\u0080\u0094": "-",
            "\u2012": "-", "\u2010": "-", "\u2011": "-",
            "\u00a0": " ", "\u200b": "", "\ufeff": "",
        }
        for ch, r in replacements.items():
            text = text.replace(ch, r)
        # Final safety net: drop anything still outside latin-1
        return text.encode("latin-1", "replace").decode("latin-1")

    def _draw_header_bar(self, pdf: FPDF, project_name: str):
        """Full-width navy top bar."""
        pdf.set_fill_color(*NAVY)
        pdf.rect(0, 0, 210, 22, "F")
        pdf.set_y(6)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*WHITE)
        pdf.cell(0, 10, f"AXIGRADE  ·  SCRIPT AUDIT  ·  {self.sanitize(project_name[:40]).upper()}", align="C")

    def _draw_footer(self, pdf: FPDF, page_num: int):
        pdf.set_y(-14)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*MID)
        pdf.cell(0, 5, f"Axigrade Quality Critic  ·  Confidential  ·  Page {page_num}", align="C")

    def create_report(
        self,
        final_scenes: list,
        original_scenes: list,
        operations: list,
        analysis: AnalysisResult,
        project_name: str = "Script_Audit"
    ) -> str:
        unique_id = uuid.uuid4().hex[:8]
        filename = f"audit_{project_name}_{unique_id}.pdf"

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=18)

        # ── PAGE 1: COVER ──────────────────────────────────────────────────
        pdf.add_page()
        self._draw_header_bar(pdf, project_name)

        # Background band
        pdf.set_fill_color(*LIGHT)
        pdf.rect(0, 22, 210, 80, "F")

        # Score circle (simulated with filled rectangle)
        cx, cy = 160, 52
        radius = 22
        # Outer ring
        pdf.set_fill_color(220, 225, 240)
        pdf.ellipse(cx - radius, cy - radius, radius * 2, radius * 2, "F")
        # Inner white
        pdf.set_fill_color(*WHITE)
        pdf.ellipse(cx - radius + 5, cy - radius + 5, (radius - 5) * 2, (radius - 5) * 2, "F")
        # Score number
        pdf.set_xy(cx - radius, cy - 9)
        pdf.set_font("Helvetica", "B", 22)
        score_color = (20, 160, 80) if analysis.score >= 80 else (200, 140, 0) if analysis.score >= 60 else (200, 50, 50)
        pdf.set_text_color(*score_color)
        pdf.cell(radius * 2, 12, str(analysis.score), align="C")
        pdf.set_xy(cx - radius, cy + 3)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*MID)
        pdf.cell(radius * 2, 5, "/ 100", align="C")
        pdf.set_xy(cx - radius, cy + 8)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*MID)
        pdf.cell(radius * 2, 5, "QUALITY SCORE", align="C")

        # Title block
        pdf.set_xy(12, 28)
        pdf.set_font("Helvetica", "B", 26)
        pdf.set_text_color(*NAVY)
        pdf.cell(130, 14, self.sanitize(project_name[:30]), ln=True)
        pdf.set_x(12)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*MID)
        pdf.cell(130, 6, "Script Quality Audit Report", ln=True)

        # Stats row
        stats = [
            ("SCENES", str(len(final_scenes))),
            ("REWRITES", str(sum(1 for op in operations if op.get("type") == "rewrite"))),
            ("ADDED",    str(sum(1 for op in operations if op.get("type") == "add"))),
            ("DELETED",  str(sum(1 for op in operations if op.get("type") == "delete"))),
            ("MERGED",   str(sum(1 for op in operations if op.get("type") == "merge"))),
            ("SPLIT",    str(sum(1 for op in operations if op.get("type") == "split"))),
        ]
        pdf.set_xy(12, 68)
        for label, val in stats:
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(*NAVY)
            pdf.cell(28, 8, val, align="C")
        pdf.ln(0)
        pdf.set_x(12)
        for label, _ in stats:
            pdf.set_font("Helvetica", "", 6)
            pdf.set_text_color(*MID)
            pdf.cell(28, 5, label, align="C")

        # Divider
        pdf.set_y(102)
        pdf.set_draw_color(*NAVY)
        pdf.set_line_width(0.4)
        pdf.line(12, pdf.get_y(), 198, pdf.get_y())
        pdf.ln(4)

        # Critique section
        pdf.set_x(12)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 7, "CRITIC'S NOTES", ln=True)
        pdf.ln(1)

        for i, point in enumerate(analysis.critique[:5]):
            pdf.set_x(12)
            # Bullet accent bar
            pdf.set_fill_color(*NAVY)
            pdf.rect(12, pdf.get_y(), 2, 0, "F")  # thin bar - skipped, use bullet

            # Numbered bullet
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*NAVY)
            pdf.set_fill_color(*LIGHT)
            pdf.cell(7, 6, f"{i+1}.", align="R")
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*DARK)
            pdf.multi_cell(175, 5, self.sanitize(point))
            pdf.ln(1)

        # Operations summary boxes
        pdf.ln(4)
        pdf.set_x(12)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 7, "OPERATIONS SUMMARY", ln=True)
        pdf.ln(2)

        op_colors = {
            "rewrite": ((255, 249, 219), (180, 120, 0), "REWRITE"),
            "delete":  ((255, 225, 225), (180, 40, 40), "DELETE"),
            "add":     ((219, 244, 230), (20, 140, 60), "ADD"),
            "merge":   ((219, 234, 255), (20, 80, 180), "MERGE"),
            "split":   ((240, 224, 255), (120, 40, 200), "SPLIT"),
        }

        x_pos = 12
        for op in operations:
            t = op.get("type", "")
            if t not in op_colors:
                continue
            bg, accent, label = op_colors[t]

            # Box
            box_w = 183
            box_h_preview = 5
            scene_ref = ""
            if t == "rewrite":
                scene_ref = f"Scene {op.get('scene_number', '?')}"
            elif t == "delete":
                scene_ref = f"Scene {op.get('scene_number', '?')}"
            elif t == "add":
                scene_ref = f"After Scene {op.get('after_scene_number', '?')}"
            elif t == "merge":
                sns = op.get("scene_numbers", [])
                scene_ref = f"Scenes {' + '.join(str(s) for s in sns)}"
            elif t == "split":
                scene_ref = f"Scene {op.get('scene_number', '?')}"

            y_now = pdf.get_y()
            if y_now > 255:
                pdf.add_page()
                self._draw_header_bar(pdf, project_name)
                pdf.set_y(28)
                y_now = pdf.get_y()

            pdf.set_fill_color(*bg)
            pdf.set_draw_color(*accent)
            pdf.set_line_width(0.3)

            # Left accent stripe
            pdf.set_fill_color(*accent)
            pdf.rect(12, y_now, 3, 12, "F")

            pdf.set_fill_color(*bg)
            pdf.rect(15, y_now, 180, 12, "F")
            pdf.set_draw_color(*accent)
            pdf.rect(15, y_now, 180, 12)

            # Label pill
            pdf.set_xy(17, y_now + 2)
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_text_color(*accent)
            pdf.cell(20, 4, label)

            # Scene ref
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_text_color(*NAVY)
            pdf.set_xy(40, y_now + 2)
            pdf.cell(30, 4, self.sanitize(scene_ref))

            # Reason
            reason = self.sanitize(op.get("reason", ""))[:80]
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*DARK)
            pdf.set_xy(75, y_now + 2)
            pdf.cell(118, 4, reason)

            pdf.set_y(y_now + 14)

        self._draw_footer(pdf, 1)

        # ── PAGE 2+: SCENE TABLE ───────────────────────────────────────────
        pdf.add_page()
        page_num = 2
        self._draw_header_bar(pdf, project_name)
        pdf.set_y(28)

        # Table title
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 7, "UPDATED SCRIPT — SCENE BY SCENE", ln=True)
        pdf.ln(2)

        # Legend
        pdf.set_x(12)
        for status, color in STATUS_COLORS.items():
            if status == "original":
                continue
            accent = STATUS_ACCENT[status]
            label = STATUS_LABEL[status]
            pdf.set_fill_color(*color)
            pdf.set_draw_color(*accent)
            pdf.rect(pdf.get_x(), pdf.get_y() + 1, 4, 4, "FD")
            pdf.set_x(pdf.get_x() + 5)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*accent)
            pdf.cell(22, 6, label)
        pdf.ln(8)

        # Table header
        def draw_table_header():
            pdf.set_fill_color(*NAVY)
            pdf.set_text_color(*WHITE)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_x(12)
            pdf.cell(10, 8, "#", border=0, fill=True, align="C")
            pdf.cell(82, 8, "SCRIPT DIALOGUE", border=0, fill=True, align="C")
            pdf.cell(82, 8, "VEO PROMPT", border=0, fill=True, align="C")
            pdf.cell(16, 8, "STATUS", border=0, fill=True, align="C")
            pdf.ln()

        draw_table_header()

        # Map original scenes for before/after lookup
        original_map = {s.scene_number: s for s in original_scenes}

        for scene in final_scenes:
            status = scene.status
            bg = STATUS_COLORS.get(status, WHITE)
            accent = STATUS_ACCENT.get(status, (100, 100, 100))
            label = STATUS_LABEL.get(status, "")

            dialogue = self.sanitize(scene.script_dialogue)
            veo = self.sanitize(scene.veo_prompt)
            scene_num = str(scene.scene_number)

            # Measure row height
            lines_d = pdf.multi_cell(82, 4.5, dialogue, split_only=True)
            lines_v = pdf.multi_cell(82, 4.5, veo, split_only=True)
            row_h = max(len(lines_d), len(lines_v)) * 4.5 + 4

            # Page break check
            if pdf.get_y() + row_h > 272:
                self._draw_footer(pdf, page_num)
                pdf.add_page()
                page_num += 1
                self._draw_header_bar(pdf, project_name)
                pdf.set_y(28)
                draw_table_header()

            x0 = 12
            y0 = pdf.get_y()

            # Row background
            pdf.set_fill_color(*bg)
            pdf.rect(x0, y0, 186, row_h, "F")

            # Left accent stripe for non-original
            if status != "original":
                pdf.set_fill_color(*accent)
                pdf.rect(x0, y0, 2, row_h, "F")

            # Draw cell borders
            pdf.set_draw_color(220, 222, 228)
            pdf.set_line_width(0.2)
            pdf.rect(x0, y0, 186, row_h)
            pdf.line(x0 + 10, y0, x0 + 10, y0 + row_h)
            pdf.line(x0 + 92, y0, x0 + 92, y0 + row_h)
            pdf.line(x0 + 174, y0, x0 + 174, y0 + row_h)

            # Scene number
            pdf.set_xy(x0, y0)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*NAVY)
            pdf.multi_cell(10, row_h, scene_num, border=0, align="C")

            # Dialogue
            pdf.set_xy(x0 + 10, y0 + 2)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*DARK)
            pdf.multi_cell(82, 4.5, dialogue, border=0)

            # VEO Prompt
            pdf.set_xy(x0 + 92, y0 + 2)
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(60, 60, 80)
            pdf.multi_cell(82, 4.5, veo, border=0)

            # Status badge
            pdf.set_xy(x0 + 174, y0 + (row_h / 2) - 3)
            if label:
                pdf.set_font("Helvetica", "B", 6)
                pdf.set_text_color(*accent)
                pdf.cell(12, 5, label, align="C")

            # Operation reason (small italic below)
            if scene.operation_reason and status != "original":
                reason_text = self.sanitize(scene.operation_reason[:60])
                pdf.set_xy(x0 + 10, y0 + row_h - 0.5)

            pdf.set_xy(x0, y0 + row_h)

        self._draw_footer(pdf, page_num)

        # ── UPLOAD TO CLOUDINARY ───────────────────────────────────────────
        temp_path = f"temp_{filename}"
        pdf.output(temp_path)

        try:
            public_id = f"scripts/audit_{project_name}_{unique_id}"
            cloudinary.uploader.upload(
                temp_path,
                public_id=public_id,
                resource_type="image",
                format="pdf",
                overwrite=True
            )
            pdf_url, _ = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type="image",
                format="pdf"
            )
            return pdf_url
        except Exception as e:
            print(f"❌ Cloudinary upload failed: {e}")
            return "error_generating_pdf"
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
