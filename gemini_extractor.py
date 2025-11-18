# gemini_extractor.py
import os
import io
import json
from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai

# Optional: helpful exception import (may or may not be installed with SDK)
try:
    from google.api_core.exceptions import NotFound
except Exception:
    NotFound = Exception

# PDF -> image
try:
    from pdf2image import convert_from_path
    _HAS_PDF2IMAGE = True
except Exception:
    _HAS_PDF2IMAGE = False

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not set in .env or environment variables")

genai.configure(api_key=API_KEY)


def _pdf_first_page_to_image(pdf_path: str, dpi=300):
    """Convert first PDF page to PIL Image. Requires pdf2image/poppler."""
    if not _HAS_PDF2IMAGE:
        raise RuntimeError("pdf2image is required to process PDFs. Install pdf2image and poppler.")
    pages = convert_from_path(pdf_path, dpi=dpi)
    if not pages:
        raise RuntimeError("No pages found in PDF.")
    return pages[0]


def _call_gemini_extract(image: Image.Image, model_name: str, prompt: str, timeout_seconds: int = 60):
    """
    Call Gemini model to extract structured JSON from an image.
    Returns the raw text response and/or parsed JSON.
    """
    try:
        model = genai.GenerativeModel(model_name)
        # Attach image as second multimodal input (SDK accepts image objects)
        resp = model.generate_content([prompt, image], generation_config={"temperature": 0.0})
        return resp
    except NotFound as e:
        # Model not found on current API version or account
        # Try to list available models (SDK may offer a listing function)
        try:
            available = genai.list_models()
            models = [m["name"] if isinstance(m, dict) and "name" in m else str(m) for m in available]
        except Exception:
            models = None
        raise RuntimeError(f"Gemini model '{model_name}' not found or not allowed for generate_content. "
                           f"Available models: {models}") from e
    except Exception as e:
        raise RuntimeError(f"Gemini request failed: {e}") from e


EXTRACTION_PROMPT = """
You are an expert invoice parser. Given the invoice image attached, extract the invoice fields in strict JSON only.
Return a JSON object exactly in this format (fill empty strings if not present):

{
  "invoice_number": "",
  "vendor": "",
  "date": "",
  "buyer": "",
  "address": "",
  "currency": "",
  "items": [
    {
      "description": "",
      "quantity": "",
      "unit_price": "",
      "tax_rate": "",
      "total_price": ""
    }
  ],
  "subtotal": "",
  "tax": "",
  "grand_total": "",
  "notes": ""
}

Return **only** the JSON (no extra commentary). Use sensible inference when possible.
"""

SUMMARY_PROMPT_TEMPLATE = """
Write a concise, professional one-sentence summary of this invoice (who, date, total, key items count):

{invoice_json}
"""


def extract_invoice_universal(file_path_or_image):
    """
    Accept either a file path (PDF/image) or a PIL.Image.Image object.
    Returns {"structured_data": dict, "raw_text": str, "summary": str}
    """
    # Accept either PIL Image or file path
    if isinstance(file_path_or_image, str):
        ext = os.path.splitext(file_path_or_image)[1].lower()
        if ext == ".pdf":
            image = _pdf_first_page_to_image(file_path_or_image)
        else:
            image = Image.open(file_path_or_image).convert("RGB")
    elif isinstance(file_path_or_image, Image.Image):
        image = file_path_or_image
    else:
        raise ValueError("file_path_or_image must be a file path string or PIL.Image.Image")

    # Call Gemini for extraction
    resp = _call_gemini_extract(image, GEMINI_MODEL, EXTRACTION_PROMPT)
    text = getattr(resp, "text", None) or str(resp)

    # Try to parse JSON substring
    try:
        json_text = text[text.find("{"): text.rfind("}") + 1]
        data = json.loads(json_text)
    except Exception:
        data = {"error": "Could not parse JSON from Gemini output", "raw_output": text}

    # Generate summary
    try:
        summary_prompt = SUMMARY_PROMPT_TEMPLATE.format(invoice_json=json.dumps(data, indent=2))
        model = genai.GenerativeModel(GEMINI_MODEL)
        sresp = model.generate_content(summary_prompt)
        summary_text = getattr(sresp, "text", None) or str(sresp)
    except Exception:
        summary_text = ""

    return {"structured_data": data, "raw_text": text, "summary": summary_text}
