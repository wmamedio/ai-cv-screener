"""Generate 25-30 realistic fake CVs as PDFs.

Pipeline per CV:  Gemini (structured JSON) -> AI photo -> Jinja HTML -> WeasyPrint PDF.

A few facts are seeded on purpose so the demo questions work:
  - one candidate named "Jane Doe"
  - two candidates who graduated from UPC (Universitat Politecnica de Catalunya)
  - a healthy number of candidates with Python experience (and several without)

Usage:  python scripts/generate_cvs.py [count]
"""
import base64
import os
import random
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from jinja2 import Template
from pydantic import BaseModel
from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

CVS_DIR = ROOT / "data" / "cvs"
PHOTO_DIR = ROOT / "data" / "photos"
PROFILE_DIR = ROOT / "data" / "profiles"
TEMPLATE = Template((Path(__file__).parent / "cv_template.html").read_text())

CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")
COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.getenv("CV_COUNT", "28"))

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
random.seed(42)

ACCENTS = ["#1e3a5f", "#0f766e", "#7c2d12", "#4338ca", "#9d174d",
           "#155e63", "#3f3f46", "#5b21b6", "#1d4ed8", "#065f46"]

ROLES = [
    "Backend Engineer", "Frontend Engineer", "Full-Stack Engineer", "Data Scientist",
    "Machine Learning Engineer", "DevOps Engineer", "iOS Developer", "Android Developer",
    "QA Automation Engineer", "UX/UI Designer", "Product Manager", "Data Engineer",
    "Cloud Solutions Architect", "Security Engineer", "Site Reliability Engineer",
    "Engineering Manager", "Business Analyst", "Digital Marketing Manager",
    "Technical Writer", "Database Administrator", "AI Research Engineer", "Game Developer",
    "Embedded Systems Engineer", "Solutions Consultant", "Network Engineer",
    "Computer Vision Engineer", "NLP Engineer", "Graphic Designer",
]
REGIONS = [
    ("Spain", "Spanish"), ("United Kingdom", "English"), ("Germany", "German"),
    ("France", "French"), ("Netherlands", "Dutch"), ("Brazil", "Portuguese"),
    ("United States", "English"), ("India", "Hindi"), ("Italy", "Italian"),
    ("Poland", "Polish"), ("Portugal", "Portuguese"), ("Sweden", "Swedish"),
    ("Canada", "English"), ("Mexico", "Spanish"), ("Ireland", "English"),
]
SENIORITIES = ["Junior", "Mid-level", "Senior", "Lead", "Principal"]
# Roles where Python is naturally a core skill.
PY_ROLES = {"Backend Engineer", "Full-Stack Engineer", "Data Scientist",
            "Machine Learning Engineer", "Data Engineer", "AI Research Engineer",
            "Computer Vision Engineer", "NLP Engineer", "DevOps Engineer"}


class Job(BaseModel):
    role: str
    company: str
    period: str
    bullets: list[str]


class Education(BaseModel):
    degree: str
    institution: str
    year: str


class Language(BaseModel):
    language: str
    level: str


class CV(BaseModel):
    name: str
    title: str
    email: str
    phone: str
    location: str
    linkedin: str
    summary: str
    skills: list[str]
    experience: list[Job]
    education: list[Education]
    languages: list[Language]
    certifications: list[str]


def build_briefs(n: int) -> list[dict]:
    briefs = []
    for i in range(n):
        role = ROLES[i % len(ROLES)]
        region, native_lang = random.choice(REGIONS)
        briefs.append({
            "role": role,
            "seniority": random.choice(SENIORITIES),
            "region": region,
            "native_lang": native_lang,
            "python": role in PY_ROLES,
            "name": None,
            "institution": None,
        })
    # Seeded facts for the demo questions (guarded so small test runs still work).
    def seed(idx, **kw):
        if idx < len(briefs):
            briefs[idx].update(**kw)

    seed(0, name="Jane Doe", role="Backend Engineer", region="United States",
         native_lang="English", python=True)
    seed(3, institution="Universitat Politecnica de Catalunya (UPC)",
         region="Spain", native_lang="Spanish")
    seed(9, institution="Universitat Politecnica de Catalunya (UPC)",
         region="Spain", native_lang="Spanish")
    # Force a couple extra Python users for a richer "who knows Python" answer.
    for idx in (2, 12, 18):
        seed(idx, python=True)
    return briefs


def generate_profile(brief: dict) -> CV:
    name_rule = (f'The candidate MUST be named "{brief["name"]}".'
                 if brief["name"] else
                 f'Invent a realistic full name typical of {brief["region"]}.')
    edu_rule = (f'At least one education entry MUST be from "{brief["institution"]}".'
                if brief["institution"] else "Use realistic universities.")
    py_rule = ("Python MUST appear prominently in skills and in at least one job's bullets."
               if brief["python"] else
               "Do NOT include Python; focus on skills natural to the role.")

    prompt = f"""Create a realistic but entirely FICTIONAL resume for a {brief['seniority']} \
{brief['role']} based in {brief['region']}.

Rules:
- {name_rule}
- {edu_rule}
- {py_rule}
- Fake but plausible contact info: professional email, phone with the correct country code, and a city in {brief['region']}.
- linkedin: a plausible linkedin.com/in/ handle based on the name.
- summary: 2-3 sentences, first person not allowed (write it as a profile blurb).
- 3-5 experience entries, newest first, each with a realistic company, a period like "Jan 2021 - Present", and 2-4 quantified achievement bullets.
- 5-9 concrete skills (tools/technologies/methods), realistic for the role and seniority.
- 1-3 education entries with degree, institution and graduation year.
- 2-3 languages with levels (e.g. Native, Fluent, B2, Conversational). Include {brief['native_lang']}.
- 0-3 certifications (can be empty).
Return ONLY the structured data."""

    last_err = None
    for attempt in range(4):
        try:
            resp = client.models.generate_content(
                model=CHAT_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=1.0,
                    response_mime_type="application/json",
                    response_schema=CV,
                ),
            )
            return resp.parsed
        except Exception as e:  # transient (rate limit / 5xx) -> backoff
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"generation failed for {brief['role']}: {last_err}")


def fetch_photo(name: str) -> str:
    """Return a data URI for an AI-generated face, with an avatar fallback."""
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    try:
        r = requests.get("https://thispersondoesnotexist.com", headers=headers, timeout=20)
        if r.status_code == 200 and r.content and r.headers.get("content-type", "").startswith("image"):
            return "data:image/jpeg;base64," + base64.b64encode(r.content).decode()
    except Exception:
        pass
    # Fallback: initials avatar (no API key required).
    try:
        r = requests.get("https://ui-avatars.com/api/",
                         params={"name": name, "size": "256", "background": "random",
                                 "color": "fff", "bold": "true"}, timeout=20)
        if r.status_code == 200:
            return "data:image/png;base64," + base64.b64encode(r.content).decode()
    except Exception:
        pass
    return ""


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_") or "candidate"


def main():
    for d in (CVS_DIR, PHOTO_DIR, PROFILE_DIR):
        d.mkdir(parents=True, exist_ok=True)

    briefs = build_briefs(COUNT)
    print(f"Generating {COUNT} CVs with {CHAT_MODEL}...\n")
    seen = set()
    for i, brief in enumerate(briefs, 1):
        cv = generate_profile(brief)
        slug = slugify(cv.name)
        while slug in seen:
            slug += "_2"
        seen.add(slug)

        photo = fetch_photo(cv.name)
        if photo:
            ext = "jpg" if "jpeg" in photo[:30] else "png"
            (PHOTO_DIR / f"{slug}.{ext}").write_bytes(base64.b64decode(photo.split(",", 1)[1]))

        (PROFILE_DIR / f"{slug}.json").write_text(cv.model_dump_json(indent=2))

        html = TEMPLATE.render(accent=ACCENTS[i % len(ACCENTS)], photo_data_uri=photo,
                               **cv.model_dump())
        HTML(string=html).write_pdf(CVS_DIR / f"{slug}.pdf")
        print(f"  [{i:2}/{COUNT}] {cv.name:28} {cv.title}")
        time.sleep(1.2)  # be gentle on the photo service / API

    print(f"\nDone. {COUNT} PDFs in {CVS_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
