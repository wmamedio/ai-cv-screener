"""Generate 25-30 realistic fake CVs as PDFs.

Pipeline per CV:  OpenAI (structured JSON) -> OpenAI gpt-image-2 (AI photo) -> Jinja HTML -> WeasyPrint PDF.

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
from jinja2 import Template
from openai import OpenAI
from pydantic import BaseModel
from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

CVS_DIR = ROOT / "data" / "cvs"
PHOTO_DIR = ROOT / "data" / "photos"
PROFILE_DIR = ROOT / "data" / "profiles"
TEMPLATE = Template((Path(__file__).parent / "cv_template.html").read_text())

CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-5.4-mini")
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
COUNT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else int(os.getenv("CV_COUNT", "28"))

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
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


def generate_profile(brief: dict, avoid: frozenset[str] = frozenset()) -> CV:
    if brief["name"]:
        name_rule = f'The candidate MUST be named "{brief["name"]}".'
    else:
        name_rule = f'Invent a realistic, UNIQUE full name typical of {brief["region"]}.'
        if avoid:
            name_rule += f' Do NOT reuse any of these already-taken names: {", ".join(sorted(avoid))}.'
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
            resp = client.chat.completions.parse(
                model=CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format=CV,
                temperature=1.0,
            )
            return resp.choices[0].message.parsed
        except Exception as e:  # transient (rate limit / 5xx) -> backoff
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"generation failed for {brief['role']}: {last_err}")


ATTIRE = ["a tailored navy blazer over a white shirt", "a charcoal blazer",
          "a smart knit sweater", "a crisp light-blue button-down shirt",
          "business-casual attire", "a dark suit jacket and open collar"]
BACKDROP = ["a softly blurred modern open-plan office", "a clean neutral grey studio backdrop",
            "a bright workspace with blurred greenery", "a softly lit office, background blurred"]
EXPRESSION = ["a warm confident smile", "a friendly approachable expression",
              "a calm professional look", "a relaxed genuine smile"]


def _age_band(title: str) -> str:
    t = title.lower()
    if "junior" in t or "intern" in t:
        return "in their mid-20s"
    if any(w in t for w in ("principal", "lead", "manager", "director", "head", "architect")):
        return "in their 40s"
    if "senior" in t:
        return "in their late 30s"
    return "in their early-to-mid 30s"


def _photo_prompt(cv: CV) -> str:
    """Shared headshot prompt. Styling is seeded off the name so re-runs are stable
    and every candidate looks distinct; gender/ethnicity are left for the image
    model to infer from the candidate's name and location."""
    rng = random.Random(cv.name)
    return (
        f"Professional corporate LinkedIn-style headshot photo of {cv.name}, "
        f"a {cv.title} based in {cv.location}, {_age_band(cv.title)}. "
        f"Tight head-and-shoulders framing, face centered, looking directly at the camera, "
        f"wearing {rng.choice(ATTIRE)}, with {rng.choice(EXPRESSION)}. "
        f"Background is {rng.choice(BACKDROP)}. Soft natural studio lighting, photorealistic, "
        f"sharp focus on the face, shot on an 85mm portrait lens. "
        f"No text, no watermark, no logo, single person only."
    )


def generate_photo(cv: CV) -> str:
    """Unique professional headshot as a data URI (gpt-image-2, avatar fallback)."""
    prompt = _photo_prompt(cv)
    return _openai_photo(prompt, cv.name) or _avatar_fallback(cv.name)


def _openai_photo(prompt: str, name: str) -> str:
    for attempt in range(3):
        try:
            # Lowest size + medium quality keeps generation fast (drop to "low" for more speed).
            r = client.images.generate(
                model=OPENAI_IMAGE_MODEL, prompt=prompt,
                size="1024x1024", quality="medium")
            return "data:image/png;base64," + r.data[0].b64_json
        except Exception as e:
            print(f"      {OPENAI_IMAGE_MODEL} attempt {attempt + 1} failed for {name}: {str(e)[:100]}")
            time.sleep(2 * (attempt + 1))  # transient (rate limit / 5xx) -> backoff
    return ""


def _avatar_fallback(name: str) -> str:
    """Initials avatar so a single image failure never blocks the CV."""
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
    seen, used_names = set(), set()
    for i, brief in enumerate(briefs, 1):
        cv = generate_profile(brief, frozenset(used_names))
        # Safety net: regenerate if the model still reused a name already taken.
        tries = 0
        while (not brief["name"] and tries < 3
               and cv.name.casefold() in {n.casefold() for n in used_names}):
            cv = generate_profile(brief, frozenset(used_names | {cv.name}))
            tries += 1
        used_names.add(cv.name)

        slug = slugify(cv.name)
        while slug in seen:
            slug += "_2"
        seen.add(slug)

        photo = generate_photo(cv)
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
