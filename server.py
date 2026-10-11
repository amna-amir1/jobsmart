"""
server.py

JobSmart AI - FastAPI Backend

Yeh file ek web server banati hai (Uvicorn ke zariye chalta hai) jo:
1. Static frontend (HTML/CSS/JS, static/ folder se) serve karta hai
2. API endpoints deta hai jinhe frontend ka JavaScript (script.js) call karta hai:
   - GET  /api/health           -> server + GROQ_API_KEY status check
   - POST /api/analyze          -> CV (PDF) + JD (text ya PDF ya image) leta
                                    hai, CV ko RAG se process karta hai, aur
                                    match score, strengths, gaps, cover
                                    letter, aur tailored CV deta hai
   - POST /api/download-pdf     -> koi bhi text ko PDF bana kar download deta hai
   - POST /api/download         -> alias (same as /api/download-pdf)

NOTE: Ye version tumhare static/script.js ke exact request format ke
mutabiq hai — script.js "jd_mode" nahi bhejta, balke seedha jo bhi field
mila ho (jd_text ya jd_file ya jd_image) wahi bhejta hai. Ye server bhi
usi tareeqe se kaam karta hai.

Chalane ka tareeqa:
    uvicorn server:app --reload

Phir browser mein: http://127.0.0.1:8000
"""

import os
import uuid
import tempfile

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from loaders import load_pdf
from llm_utils import (
    analyze_cv_against_jd,
    generate_cover_letter,
    generate_tailored_cv,
    extract_jd_from_image,
)
from pdf_utils import text_to_pdf
from rag_pipeline import split_text_into_chunks, store_chunks, retrieve_relevant_chunks

load_dotenv()

# Kitne relevant CV chunks JD ke against retrieve karne hain
RAG_TOP_K = 8

app = FastAPI(title="JobSmart AI")

# CORS: taake frontend (agar kabhi alag jagah se serve ho) backend ko call kar sake
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _pdf_upload_to_text(file_bytes: bytes) -> str:
    """UploadFile ke raw bytes ko temp PDF mein save kar ke text nikalta hai."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        return load_pdf(tmp_path)
    finally:
        os.remove(tmp_path)


@app.get("/api/health")
def health():
    """Frontend ye check karne ke liye use karta hai ke backend zinda hai aur API key set hai."""
    key = os.getenv("GROQ_API_KEY")
    has_key = bool(key) and key != "your_api_key_here"
    return {"status": "ok", "groq_key_configured": has_key}


@app.post("/api/analyze")
async def analyze(
    cv_file: UploadFile = File(...),
    jd_text: str = Form(""),
    jd_file: UploadFile | None = File(None),
    jd_image: UploadFile | None = File(None),
):
    """
    CV (PDF) + Job Description (jd_text ya jd_file ya jd_image, jo bhi
    diya gaya ho) leta hai. CV ko RAG (chunking + vector search) se
    process karta hai, phir analysis + cover letter + tailored CV,
    teeno ek response mein deta hai.
    """
    key = os.getenv("GROQ_API_KEY")
    if not key or key == "your_api_key_here":
        raise HTTPException(
            status_code=400,
            detail="GROQ_API_KEY is not set. Add your Groq key to the .env file and restart the server.",
        )

    # ---- CV text nikalna ----
    cv_bytes = await cv_file.read()
    try:
        cv_text = _pdf_upload_to_text(cv_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CV PDF: {e}")

    if not cv_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract any text from the CV. Is the PDF a scanned image?")

    # ---- JD text nikalna: jo bhi field diya gaya ho (text / pdf / image) ----
    jd_final_text = (jd_text or "").strip()

    if not jd_final_text and jd_file is not None and jd_file.filename:
        try:
            jd_bytes = await jd_file.read()
            jd_final_text = _pdf_upload_to_text(jd_bytes).strip()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading JD PDF: {e}")

    if not jd_final_text and jd_image is not None and jd_image.filename:
        try:
            image_bytes = await jd_image.read()
            media_type = jd_image.content_type or "image/png"
            jd_final_text = extract_jd_from_image(image_bytes, media_type=media_type).strip()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing JD image: {e}")

    if not jd_final_text:
        raise HTTPException(status_code=400, detail="Job description is empty. Provide text, a PDF, or an image.")

    # ---- RAG: CV ko chunks mein tod kar, JD se relevant hisse retrieve karna ----
    try:
        chunks = split_text_into_chunks(cv_text)
        # Har request ke liye alag, temporary (memory-only) collection —
        # taake alag alag users/CVs ka data aapas mein mix na ho.
        collection_name = f"cv_{uuid.uuid4().hex}"
        vectorstore = store_chunks(chunks, collection_name=collection_name, persist_directory=None)
        relevant_chunks = retrieve_relevant_chunks(vectorstore, jd_final_text, k=min(RAG_TOP_K, len(chunks)))
        cv_context = "\n\n".join(relevant_chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in RAG chunking/retrieval: {e}")

    if not cv_context.strip():
        # Fallback: agar retrieval kuch na de to poori CV hi use kar lo
        cv_context = cv_text

    # ---- Groq se teeno cheezein generate karna (RAG se aaye relevant context ke sath) ----
    try:
        analysis = analyze_cv_against_jd(cv_context, jd_final_text)
        cover_letter = generate_cover_letter(cv_context, jd_final_text)
        tailored_cv = generate_tailored_cv(cv_context, jd_final_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting a response from the AI: {e}")

    return {
        "analysis": analysis,
        "cover_letter": cover_letter,
        "tailored_cv": tailored_cv,
    }


@app.post("/api/download")
@app.post("/api/download-pdf")   # alias — dono naam se call kiya ja sakta hai
async def download_pdf(
    text: str = Form(...),
    title: str = Form(""),
    filename: str = Form("document.pdf"),
):
    """Diya gaya text ek styled PDF mein convert kar ke download ke liye deta hai."""
    safe_filename = filename if filename.endswith(".pdf") else f"{filename}.pdf"
    out_path = os.path.join(tempfile.gettempdir(), safe_filename)
    try:
        text_to_pdf(text, out_path, doc_title=title)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {e}")
    return FileResponse(out_path, media_type="application/pdf", filename=safe_filename)


# Static frontend (HTML/CSS/JS) serve karna.
# NOTE: Yeh sabse aakhir mein mount hona chahiye, warna API routes cover ho jayenge.
app.mount("/", StaticFiles(directory="static", html=True), name="static")