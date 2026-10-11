"""
app.py

JobSmart AI - Streamlit Frontend

Kya karta hai:
1. User apni CV (PDF) upload karta hai
2. Job description text paste kar sakta hai, PDF upload kar sakta hai,
   ya JD ki image/screenshot upload kar sakta hai
3. "Analyze" par click karne se:
   - CV ko JD ke against rate kiya jata hai (score + strengths + gaps)
   - Ek tailored cover letter generate hoti hai (PDF download ke saath)
   - Ek JD ke hisaab se behtar CV generate hoti hai (PDF download ke saath)

Chalane ka tarika:
    streamlit run app.py
"""

import os
import tempfile

import streamlit as st

from loaders import load_pdf
from llm_utils import (
    analyze_cv_against_jd,
    generate_cover_letter,
    generate_tailored_cv,
    extract_jd_from_image,
)
from pdf_utils import text_to_pdf


# ----------------------------- Page setup -----------------------------

st.set_page_config(
    page_title="JobSmart AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    .main {
        background-color: #0f1420;
    }
    .stApp {
        background: linear-gradient(180deg, #10131f 0%, #161b2c 100%);
    }
    h1, h2, h3 {
        font-family: 'Segoe UI', sans-serif;
    }
    .hero-title {
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(90deg, #6366f1, #22d3ee);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .hero-subtitle {
        color: #9ca3af;
        font-size: 1.05rem;
        margin-top: 0.2rem;
    }
    .score-card {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 18px;
        padding: 1.6rem 1.8rem;
        text-align: center;
    }
    .score-number {
        font-size: 3.2rem;
        font-weight: 800;
    }
    .verdict-badge {
        display: inline-block;
        padding: 0.3rem 1rem;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.95rem;
        margin-top: 0.4rem;
    }
    .panel {
        background: #161b2c;
        border: 1px solid #262c40;
        border-radius: 16px;
        padding: 1.3rem 1.5rem;
        margin-bottom: 1rem;
    }
    .panel h4 {
        margin-top: 0;
    }
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        padding: 0.55rem 1.4rem;
    }
    .stDownloadButton>button {
        border-radius: 10px;
        font-weight: 600;
        width: 100%;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ----------------------------- Helper functions -----------------------------

def save_uploaded_pdf_and_extract_text(uploaded_file) -> str:
    """Streamlit ki uploaded PDF file ko temp path pe save kar ke text nikalta hai."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    try:
        return load_pdf(tmp_path)
    finally:
        os.remove(tmp_path)


def score_color(score: int) -> str:
    if score >= 75:
        return "#22c55e"   # green
    if score >= 50:
        return "#eab308"   # yellow
    return "#ef4444"       # red


def get_jd_text(jd_mode: str) -> str:
    """Selected tab ke hisaab se JD ka text return karta hai (ya khali string)."""
    if jd_mode == "paste":
        return st.session_state.get("jd_paste_text", "").strip()

    if jd_mode == "pdf":
        jd_pdf = st.session_state.get("jd_pdf_file")
        if jd_pdf is not None:
            return save_uploaded_pdf_and_extract_text(jd_pdf).strip()
        return ""

    if jd_mode == "image":
        jd_image = st.session_state.get("jd_image_file")
        if jd_image is not None:
            media_type = jd_image.type or "image/png"
            return extract_jd_from_image(jd_image.getvalue(), media_type=media_type).strip()
        return ""

    return ""


# ----------------------------- Sidebar -----------------------------

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    api_key_input = st.text_input(
        "Groq API Key",
        value=os.getenv("GROQ_API_KEY", ""),
        type="password",
        help="Agar .env file mein pehle se key set hai to yeh khali chhor sakte hain. "
             "Free key: https://console.groq.com/keys",
    )
    if api_key_input:
        os.environ["GROQ_API_KEY"] = api_key_input

    st.markdown("---")
    st.markdown(
        "**JobSmart AI** tumhari CV ko job description ke against analyze karta "
        "hai, ek match score deta hai, aur tumhare liye tailored cover letter "
        "aur behtar CV bana kar deta hai."
    )
    st.markdown("---")
    st.caption("Made with Streamlit + Groq")


# ----------------------------- Hero header -----------------------------

st.markdown('<p class="hero-title">🎯 JobSmart AI</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-subtitle">Apni CV upload karein, job description dein, '
    'aur match score, tailored cover letter aur behtar CV paayein — sab ek jagah.</p>',
    unsafe_allow_html=True,
)
st.write("")

# ----------------------------- Upload section -----------------------------

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("#### 📄 Apni CV Upload Karein")
    cv_file = st.file_uploader("CV (PDF)", type=["pdf"], label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("#### 💼 Job Description Dein")

    jd_tab = st.radio(
        "JD ka tarika",
        options=["Text Paste Karein", "PDF Upload Karein", "Image/Screenshot Upload Karein"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if jd_tab == "Text Paste Karein":
        st.text_area(
            "JD Text",
            key="jd_paste_text",
            height=180,
            placeholder="Job description yahan paste karein...",
            label_visibility="collapsed",
        )
        jd_mode = "paste"

    elif jd_tab == "PDF Upload Karein":
        st.file_uploader("JD PDF", type=["pdf"], key="jd_pdf_file", label_visibility="collapsed")
        jd_mode = "pdf"

    else:
        st.file_uploader(
            "JD Image", type=["png", "jpg", "jpeg"], key="jd_image_file",
            label_visibility="collapsed",
        )
        jd_mode = "image"

    st.markdown("</div>", unsafe_allow_html=True)

st.write("")
analyze_clicked = st.button("🚀 Analyze karein", use_container_width=True, type="primary")


# ----------------------------- Analysis flow -----------------------------

if analyze_clicked:
    if not os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") == "your_api_key_here":
        st.error("Pehle sidebar mein apni Groq API key daal dein.")
    elif cv_file is None:
        st.error("Pehle apni CV (PDF) upload karein.")
    else:
        with st.spinner("CV padhi ja rahi hai..."):
            cv_text = save_uploaded_pdf_and_extract_text(cv_file)

        with st.spinner("Job description process ho rahi hai..."):
            try:
                jd_text = get_jd_text(jd_mode)
            except Exception as e:
                st.error(f"JD process karte waqt masla aaya: {e}")
                jd_text = ""

        if not jd_text:
            st.error("Job description khali hai. Text paste karein ya PDF/image upload karein.")
        else:
            try:
                with st.spinner("CV ko job description ke against analyze kiya ja raha hai..."):
                    analysis = analyze_cv_against_jd(cv_text, jd_text)

                with st.spinner("Tailored cover letter likhi ja rahi hai..."):
                    cover_letter = generate_cover_letter(cv_text, jd_text)

                with st.spinner("Behtar CV banayi ja rahi hai..."):
                    tailored_cv = generate_tailored_cv(cv_text, jd_text)

                st.session_state["analysis"] = analysis
                st.session_state["cover_letter"] = cover_letter
                st.session_state["tailored_cv"] = tailored_cv
                st.session_state["analyzed"] = True

            except Exception as e:
                st.error(f"Kuch masla ho gaya: {e}")


# ----------------------------- Results -----------------------------

if st.session_state.get("analyzed"):
    analysis = st.session_state["analysis"]
    cover_letter = st.session_state["cover_letter"]
    tailored_cv = st.session_state["tailored_cv"]

    st.write("---")
    st.markdown("### 📊 Match Analysis")

    score = int(analysis.get("overall_score", 0))
    verdict = analysis.get("verdict", "")
    strengths = analysis.get("strengths", [])
    gaps = analysis.get("gaps", [])
    recommendation = analysis.get("recommendation", "")

    color = score_color(score)

    res_col1, res_col2 = st.columns([1, 2], gap="large")

    with res_col1:
        st.markdown(
            f"""
            <div class="score-card">
                <div style="color:#9ca3af; font-size:0.95rem;">Overall Match Score</div>
                <div class="score-number" style="color:{color};">{score}<span style="font-size:1.4rem;">/100</span></div>
                <div class="verdict-badge" style="background:{color}22; color:{color};">{verdict}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with res_col2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("**💡 Recommendation**")
        st.write(recommendation)
        st.markdown("</div>", unsafe_allow_html=True)

    strength_col, gap_col = st.columns(2, gap="large")

    with strength_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("#### ✅ Strengths")
        for s in strengths:
            st.markdown(f"- {s}")
        st.markdown("</div>", unsafe_allow_html=True)

    with gap_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("#### ⚠️ Gaps")
        for g in gaps:
            st.markdown(f"- {g}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("---")
    st.markdown("### 📥 Downloads")

    dl_col1, dl_col2 = st.columns(2, gap="large")

    with dl_col1:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("#### ✉️ Tailored Cover Letter")
        with st.expander("Preview"):
            st.write(cover_letter)

        cl_path = os.path.join(tempfile.gettempdir(), "cover_letter.pdf")
        text_to_pdf(cover_letter, cl_path, doc_title="Cover Letter")
        with open(cl_path, "rb") as f:
            st.download_button(
                "⬇️ Cover Letter (PDF) Download Karein",
                data=f.read(),
                file_name="cover_letter.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with dl_col2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("#### 📄 Tailored CV")
        with st.expander("Preview"):
            st.write(tailored_cv)

        cv_path = os.path.join(tempfile.gettempdir(), "tailored_cv.pdf")
        text_to_pdf(tailored_cv, cv_path, doc_title="")
        with open(cv_path, "rb") as f:
            st.download_button(
                "⬇️ Tailored CV (PDF) Download Karein",
                data=f.read(),
                file_name="tailored_cv.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)