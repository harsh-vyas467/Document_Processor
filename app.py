import os
import tempfile
import json
import fitz  # PyMuPDF
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
import google.generativeai as genai
from pathlib import Path

# ----------------------
# CONFIGURATION
# ----------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables or .env")

genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# ----------------------
# LOAD LANGUAGES FROM JSON FILE
# ----------------------
with open("languages.json", "r", encoding="utf-8") as f:
    LANGUAGES = json.load(f)

# ----------------------
# PROMPT TEMPLATES
# ----------------------
def prompt_json(text, target_language):
    return f"""
Please analyze the following document text.

Instructions:
1. Detect the original language automatically.
2. Translate all text into {target_language}.
3. Provide the result in this exact JSON format (valid JSON, no extra text outside the JSON):

{{
  "doc_type": "auto-detected document type (e.g., invoice, contract, letter, etc.)",
  "metadata": {{
    "detected_language": "ISO language code (e.g., 'ja', 'zh', 'ko', 'en')",
    "confidence": float_between_0_and_1
  }},
  "entities": {{
    // Extract all identifiable information as key-value pairs
    // Use descriptive keys written in {target_language}
  }},
  "full_translated_text": "Full translation of the document in {target_language}"
}}

4. Preserve numbers, dates, and currency formats exactly as in the original.
5. If any content is unreadable, replace it with "[unreadable]".
6. Include all readable information from the document without summarizing or omitting.

Document text:
{text}
"""

def prompt_translate(text, target_language):
    return f"""
You are a professional document translator.

Instructions:
1. Detect the original language automatically.
2. Translate the entire document into {target_language}.
3. Maintain the original document's formatting as much as possible.
4. Only translate text; do not alter non-text elements.

Document text:
{text}
"""

def prompt_summary(text, target_language):
    return f"""
You are a professional summarizer.

Instructions:
1. Detect the document's original language automatically.
2. Generate a **detailed summary** in {target_language}.
3. Do not omit important details (names, dates, amounts).
4. Keep the summary concise but complete.

Document text:
{text}
"""

def prompt_detect_language(text):
    return f"""
Please analyze the following document text and detect its original language.

Instructions:
1. Identify the language of the text.
2. Provide the result in JSON format:
{{
    "detected_language": "A string containing the full name of the language followed by its ISO 639-1 code in parentheses (e.g., "Japanese (ja)", "Chinese (zh)", "Korean (ko)", "English (en)")",
    "confidence": float_between_0_and_1
}}

3. Only include the JSON object in your response.

Document text:
{text}
"""

# ----------------------
# GEMINI CALLS
# ----------------------
def call_gemini(prompt):
    # Configure safety settings to avoid blocking content
    safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE",
        },
    ]
    
    # Configure generation parameters
    generation_config = {
        "temperature": 0.3,  # Less creative, more factual
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,  # Support longer documents
    }
    
    model = genai.GenerativeModel(
        "gemini-2.0-flash-lite",
        safety_settings=safety_settings,
        generation_config=generation_config
    )
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        app.logger.error(f"Gemini API error: {str(e)}")
        return None

# ----------------------
# PDF HELPERS
# ----------------------
def extract_text_with_positions(pdf_path):
    doc = fitz.open(pdf_path)
    pages_data = []
    for page_num, page in enumerate(doc):
        blocks = page.get_text("blocks")
        page_items = []
        for b in blocks:
            x0, y0, x1, y1, text, block_no, block_type = b
            if text.strip() and block_type == 0:  # Only process text blocks
                page_items.append({
                    "bbox": (x0, y0, x1, y1),
                    "text": text,
                    "block_no": block_no
                })
        pages_data.append(page_items)
    return pages_data

def rebuild_pdf_with_translation(pdf_path, translated_texts, output_path):
    doc = fitz.open(pdf_path)
    for page_num, page in enumerate(doc):
        page_items = translated_texts[page_num]
        for item in page_items:
            bbox = item["bbox"]
            page.add_redact_annot(bbox, fill=(1, 1, 1))
        page.apply_redactions()
        for item in page_items:
            bbox = item["bbox"]
            text = item["text"]
            # Calculate font size based on bounding box height
            font_size = max(8, min(14, (bbox[3] - bbox[1]) * 0.7))
            page.insert_text(
                fitz.Point(bbox[0], bbox[1] + font_size * 0.8),  # Better vertical alignment
                text,
                fontname="helv",
                fontsize=font_size,
                color=(0, 0, 0)
            )
    doc.save(output_path)

# ----------------------
# CUSTOM PROMPT HANDLER
# ----------------------
def handle_custom_instructions(text, target_language, custom_instructions):
    """
    Processes custom instructions by replacing placeholders with actual values
    """
    return custom_instructions.replace("{text}", text).replace("{target_language}", target_language)

# ----------------------
# LANGUAGE DETECTION
# ----------------------
def detect_document_language(text):
    """Detects document language using a dedicated prompt"""
    if not text.strip():
        return None, None
        
    prompt = prompt_detect_language(text)
    response = call_gemini(prompt)
    
    if not response:
        return None, None
        
    try:
        # Extract JSON from response
        start = response.find('{')
        end = response.rfind('}') + 1
        json_str = response[start:end]
        data = json.loads(json_str)
        return data.get("detected_language"), data.get("confidence")
    except (json.JSONDecodeError, KeyError) as e:
        app.logger.error(f"Language detection parse error: {str(e)}")
        return None, None

# ----------------------
# ROUTES
# ----------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Get form data
        file = request.files["file"]
        target_language = request.form.get("target_language", "en")
        outputs_selected = request.form.getlist("outputs")  # ["json", "pdf", "summary"]
        
        # Get custom instructions
        custom_json_instructions = request.form.get("custom_json_instructions", "").strip()
        custom_pdf_instructions = request.form.get("custom_pdf_instructions", "").strip()
        custom_summary_instructions = request.form.get("custom_summary_instructions", "").strip()

        # Process uploaded file
        filename = secure_filename(file.filename)
        temp_dir = tempfile.mkdtemp()
        input_pdf_path = os.path.join(temp_dir, filename)
        file.save(input_pdf_path)

        # Extract text from PDF
        text = ""
        with fitz.open(input_pdf_path) as doc:
            for page in doc:
                text += page.get_text()

        # Initialize results
        results = {
            "detected_language": None,
            "confidence": None,
            "summary": None,
            "files": []
        }

        # Always detect language regardless of selected outputs
        detected_lang, confidence = detect_document_language(text)
        results["detected_language"] = detected_lang
        results["confidence"] = confidence

        # JSON processing
        if "json" in outputs_selected:
            if custom_json_instructions:
                prompt = handle_custom_instructions(text, target_language, custom_json_instructions)
            else:
                prompt = prompt_json(text, target_language)
            
            gemini_output = call_gemini(prompt)
            
            if gemini_output:
                try:
                    # Extract JSON from response
                    start = gemini_output.find('{')
                    end = gemini_output.rfind('}') + 1
                    json_str = gemini_output[start:end]
                    json_data = json.loads(json_str)
                    
                    # Update language info if available (more accurate)
                    if "metadata" in json_data:
                        results["detected_language"] = json_data["metadata"].get("detected_language", detected_lang)
                        results["confidence"] = json_data["metadata"].get("confidence", confidence)
                    
                    json_path = OUTPUT_DIR / f"{Path(filename).stem}_output.json"
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)
                    results["files"].append({"label": "JSON Output", "filename": json_path.name})
                except (json.JSONDecodeError, KeyError) as e:
                    app.logger.error(f"JSON processing error: {str(e)}")
                    results["files"].append({"label": "JSON Output", "error": "Processing failed"})
            else:
                results["files"].append({"label": "JSON Output", "error": "API call failed"})

        # PDF processing
        if "pdf" in outputs_selected:
            pages_data = extract_text_with_positions(input_pdf_path)
            translated_pages = []
            
            # Group text by page
            for page_items in pages_data:
                page_text = ""
                text_blocks = []
                
                # Sort items by vertical position then horizontal position
                page_items.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))
                
                for item in page_items:
                    page_text += item["text"] + "\n"
                    text_blocks.append(item)
                
                if custom_pdf_instructions:
                    prompt = handle_custom_instructions(page_text, target_language, custom_pdf_instructions)
                else:
                    prompt = prompt_translate(page_text, target_language)
                
                translated_text = call_gemini(prompt)
                
                if translated_text:
                    # Split into lines while preserving paragraphs
                    translated_lines = [line.strip() for line in translated_text.split('\n') if line.strip()]
                    
                    # Assign translated text back to blocks
                    translated_items = []
                    for i, item in enumerate(text_blocks):
                        if i < len(translated_lines):
                            translated_items.append({
                                "bbox": item["bbox"],
                                "text": translated_lines[i]
                            })
                        else:
                            # If we have more blocks than lines, use original text
                            translated_items.append({
                                "bbox": item["bbox"],
                                "text": item["text"]
                            })
                    translated_pages.append(translated_items)
                else:
                    # Fallback to original text if translation fails
                    translated_pages.append(page_items)
            
            pdf_path = OUTPUT_DIR / f"{Path(filename).stem}_translated.pdf"
            rebuild_pdf_with_translation(input_pdf_path, translated_pages, str(pdf_path))
            results["files"].append({"label": "Translated PDF", "filename": pdf_path.name})

        # Summary processing
        if "summary" in outputs_selected:
            if custom_summary_instructions:
                prompt = handle_custom_instructions(text, target_language, custom_summary_instructions)
            else:
                prompt = prompt_summary(text, target_language)
            
            summary_text = call_gemini(prompt)
            if summary_text:
                results["summary"] = summary_text
            else:
                results["summary"] = "Summary generation failed"

            # Get summary format
            summary_format = request.form.get("summary_format", "txt")

            if summary_text:  # Only create files if summary was generated
                if summary_format == "txt":
                    summary_path = OUTPUT_DIR / f"{Path(filename).stem}_summary.txt"
                    with open(summary_path, "w", encoding="utf-8") as f:
                        f.write(summary_text)
                    results["files"].append({"label": "Summary (TXT)", "filename": summary_path.name})

                elif summary_format == "pdf":
                    from reportlab.lib.pagesizes import A4
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.styles import getSampleStyleSheet
                    from reportlab.platypus import Paragraph, SimpleDocTemplate

                    summary_path = OUTPUT_DIR / f"{Path(filename).stem}_summary.pdf"
                    
                    # Create PDF with proper wrapping
                    doc = SimpleDocTemplate(
                        str(summary_path),
                        pagesize=A4,
                        rightMargin=50,
                        leftMargin=50,
                        topMargin=50,
                        bottomMargin=50
                    )
                    
                    styles = getSampleStyleSheet()
                    story = []
                    p = Paragraph(summary_text.replace('\n', '<br/>'), styles["Normal"])
                    story.append(p)
                    
                    doc.build(story)
                    results["files"].append({"label": "Summary (PDF)", "filename": summary_path.name})

        # Prepare result variables
        detected_language = results["detected_language"] or "Unknown"
        confidence = results["confidence"] or "N/A"
        summary_text = results["summary"] or ""
        files = results["files"]

        # Clean up temporary files
        try:
            os.remove(input_pdf_path)
            os.rmdir(temp_dir)
        except OSError as e:
            app.logger.error(f"Error cleaning temp files: {str(e)}")

        return render_template(
            "result.html",
            detected_language=detected_language,
            confidence=confidence,
            summary=summary_text,
            files=files
        )

    return render_template("index.html", languages=LANGUAGES)

@app.route("/download/<filename>")
def download_file(filename):
    file_path = OUTPUT_DIR / filename
    if file_path.exists():
        return send_file(file_path, as_attachment=True)
    return "File not found", 404

# ----------------------
# MAIN
# ----------------------
if __name__ == "__main__":
    app.run(debug=True)