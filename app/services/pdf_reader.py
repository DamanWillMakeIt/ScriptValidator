import httpx
import io
from pypdf import PdfReader

class PDFReaderService:
    async def download_and_parse(self, url: str) -> str:
        """
        Downloads a file from a URL and returns its text content.
        Supports .pdf and .txt
        """
        print(f"⬇️ Downloading script from: {url}")
        
        async with httpx.AsyncClient() as client:
            try:
                # Follow redirects is important for shared links (like Google Drive/Dropbox)
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                content_bytes = response.content
            except Exception as e:
                print(f"❌ Download failed: {e}")
                return ""

        # Detect File Type based on URL extension
        lower_url = url.lower()
        
        # --- CASE A: PDF ---
        if lower_url.endswith(".pdf"):
            try:
                reader = PdfReader(io.BytesIO(content_bytes))
                text = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
                return text.strip()
            except Exception as e:
                print(f"❌ PDF Parsing failed: {e}")
                return ""
        
        # --- CASE B: TEXT FILE (or unknown) ---
        else:
            try:
                # Try UTF-8 first
                return content_bytes.decode('utf-8').strip()
            except:
                # Fallback to Latin-1 if UTF-8 fails
                return content_bytes.decode('latin-1').strip()