# AI CV Screener — Plan

Scope: the 3 core requirements only. Lean, no over-engineering.

## 1. CV Generation  ✅
- [x] `scripts/generate_cvs.py`: Gemini generates 25–30 varied profiles (JSON)
- [x] Diverse roles/names/locations/languages; seed known facts for demo
      (2 UPC grads, 11 Python users, a "Jane Doe")
- [x] AI photo per CV via thispersondoesnotexist.com (avatar fallback)
- [x] HTML/Jinja template → PDF (photo, contact, experience, skills, education)
- [x] Output 28 files to `data/cvs/*.pdf`

## 2. RAG Workflow  ✅
- [x] `backend/ingest.py`: extract PDF text (pypdf) → embed → Chroma (1 vec/CV)
- [x] `backend/rag.py`: embed question → similarity search (k=12) → grounded prompt → Gemini
- [x] Grounding: answer only from CV context; says so when not found (verified)
- [x] Return source CV filenames with each answer
- [x] `backend/app.py`: FastAPI `/chat` endpoint

## 3. Chat Interface
- [ ] React + Vite + TS + Tailwind chat page
- [ ] Text input + answer display + source CVs shown
- [ ] Wire to `/chat`

## Deliverable wrap-up
- [ ] README quick start verified end-to-end
- [ ] Architecture diagram (in README, Mermaid) — for the overview-diagram deliverable
- [ ] Sample questions work (Python / UPC / Jane Doe)

## Review
(filled in when done)
