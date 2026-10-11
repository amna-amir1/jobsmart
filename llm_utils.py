"""
llm_utils.py

Groq API ke saath saara "smart" kaam:
1. CV ko JD ke against rate karna (score + strengths + gaps)
2. Tailored cover letter likhna
3. JD ke mutabiq behtar/tailored CV likhna
4. JD image se text nikalna (vision model)

API key .env file se GROQ_API_KEY ke naam se li jati hai.
Free key: https://console.groq.com/keys
"""

import os
import json
import base64
import re

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

TEXT_MODEL = "openai/gpt-oss-120b"
VISION_MODEL = "qwen/qwen3.6-27b"


def get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise ValueError(
            "GROQ_API_KEY nahi mili. .env file mein apni Groq API key daalein "
            "(free key: https://console.groq.com/keys)."
        )
    return Groq(api_key=api_key)


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("Model ke response se valid JSON nahi nikal saka.")


def extract_jd_from_image(image_bytes: bytes, media_type: str = "image/png") -> str:
    client = get_client()
    b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{media_type};base64,{b64_image}"

    response = client.chat.completions.create(
        model=VISION_MODEL,
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Is image mein ek job description hai. Iska poora text "
                            "accurately transcribe kar ke plain text mein likhein. "
                            "Sirf transcription do, koi extra comment nahi."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    )
    return response.choices[0].message.content.strip()


def analyze_cv_against_jd(cv_text: str, jd_text: str) -> dict:
    client = get_client()

    prompt = f"""Tum ek expert technical recruiter ho. Neeche ek candidate ki CV aur
ek job description (JD) di gayi hai. In dono ko compare kar ke candidate ki
suitability ka honest, mehnat se socha hua analysis do.

CV:
---
{cv_text}
---

JOB DESCRIPTION:
---
{jd_text}
---

Sirf neeche diye gaye JSON format mein jawab do, koi extra text nahi, koi markdown
code fence nahi:

{{
  "overall_score": <0 se 100 tak ek integer, kitna acha match hai>,
  "verdict": "<ek chhota jumla, jaise 'Strong Match' ya 'Partial Match' ya 'Weak Match'>",
  "strengths": ["<candidate ki wo skills/experience jo JD se match karti hain>", "..."],
  "gaps": ["<wo requirements jo CV mein missing ya kamzor hain>", "..."],
  "recommendation": "<2-3 jumlon mein overall advice, candidate ko kya improve karna chahiye>"
}}
"""

    response = client.chat.completions.create(
        model=TEXT_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return _extract_json(response.choices[0].message.content)


def generate_cover_letter(cv_text: str, jd_text: str, candidate_name: str = "") -> str:
    client = get_client()

    name_instruction = (
        f"Candidate ka naam '{candidate_name}' hai, isay letter mein use karo."
        if candidate_name
        else "CV se candidate ka naam nikaalne ki koshish karo; agar na mile to generic rakho."
    )

    prompt = f"""Tum ek professional career writer ho. Neeche di gayi CV aur job
description ke hisaab se ek achi, tailored, professional cover letter likho.

{name_instruction}

Cover letter:
- Achay tone mein ho, na zyada formal na casual
- Candidate ki relevant skills aur experience ko JD ki requirements se jodo
- 3-4 paragraphs ki ho
- Proper letter format mein ho (greeting, body, closing)
- Sirf letter ka text do, koi extra commentary nahi
- BOHOT ZAROORI: koi bhi markdown symbols use na karo (** bold ke liye, # heading
  ke liye, * bullet ke liye waghera) — sirf plain, clean text likho jaise koi
  insaan Word mein type karta hai.

CV:
---
{cv_text}
---

JOB DESCRIPTION:
---
{jd_text}
---
"""

    response = client.chat.completions.create(
        model=TEXT_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def generate_tailored_cv(cv_text: str, jd_text: str) -> str:
    client = get_client()

    prompt = f"""Tum ek professional resume writer ho. Neeche candidate ki original
CV aur ek job description di gayi hai. Is CV ko job description ke hisaab se
behtar bana kar rewrite karo — relevant skills/experience ko highlight karo,
weak ya irrelevant hisse chhota karo, aur professional, ATS-friendly resume
language use karo.

BOHOT ZAROORI RULE (ethics/honesty):
- Sirf wahi experience, skills, aur achievements likho jo ORIGINAL CV mein
  pehle se maujood hain. Koi naya job title, degree, certification, ya
  experience MAT BANAO jo candidate ke paas nahi hai.
- Agar job description ki koi requirement CV mein bilkul match nahi karti
  (jaise CV ek developer ki hai magar JD "trainer" ya kisi bilkul alag field
  ke liye hai), to us requirement ko fabricate mat karo. Iski jagah candidate
  ki maujooda experience mein se jo transferable/related hissa ho (jaise team
  leadership, mentoring, documentation, presentations) usay JD ki zubaan mein
  reframe karo — lekin sirf agar wo waqai CV mein mojood ho.
- Jhooti ya ghalat information CV mein likhna candidate ko interview mein
  bura position mein daal sakta hai — is liye honesty sabse zaroori hai.

Output ek clean, well-organized resume ki tarah honi chahiye in sections mein:
- Candidate ka naam aur contact info (agar CV mein mojood ho) — sab ek hi line
  mein, pipe (|) se separate: Phone | Email | LinkedIn | GitHub
- Professional Summary (2-3 lines, JD ke hisaab se tailored, sirf sachi baatein)
- Technical Skills
- Experience (bullet points mein, achievements ke saath — jahan CV mein numbers/
  metrics diye hon wahan unhe zaroor include karo, jaise "%", "reduced by",
  "increased by")
- Projects (agar CV mein hain)
- Education

Formatting rules (BOHOT ZAROORI, ATS ke liye plain text zaroori hai):
- Section headings ke liye sirf "## " prefix use karo (jaise "## Professional Summary")
- Candidate ke naam ke liye sirf "# " prefix use karo (sabse pehli line)
- Bullet points ke liye sirf "- " prefix use karo
- Kahin bhi "**" (double asterisk / bold markdown) BILKUL use NA karo — koi bhi
  lafz ko bold dikhane ke liye "**" mat lagao, sirf plain text likho
- Koi italics (*text*) ya doosre markdown symbols bhi use na karo
- Hyphenated words (jaise "hands-on", "end-to-end") mein hyphen zaroor rakho,
  usay mat hatao
- Sirf resume ka content do, koi extra commentary ya explanation nahi

ORIGINAL CV:
---
{cv_text}
---

JOB DESCRIPTION:
---
{jd_text}
---
"""

    response = client.chat.completions.create(
        model=TEXT_MODEL,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()