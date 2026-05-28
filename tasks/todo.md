# AI CV Screener — Plan

Scope: the 3 core requirements only. Lean, no over-engineering.

## 1. CV Generation
- [ ] `scripts/generate_cvs.py`: Gemini generates 25–30 varied profiles (JSON)
- [ ] Diverse roles/names/locations/languages; seed known facts for demo
      (a candidate from UPC, several Python users, a "Jane Doe")
- [ ] AI photo per CV via thispersondoesnotexist.com
- [ ] HTML/Jinja template → PDF (photo, contact, experience, skills, education)
- [ ] Output 25–30 files to `data/cvs/*.pdf`

## 2. RAG Workflow
- [ ] `backend/ingest.py`: extract PDF text (pypdf) → chunk → embed → Chroma
- [ ] `backend/rag.py`: embed question → similarity search → grounded prompt → Gemini
- [ ] Grounding: answer only from CV context; say so when not found
- [ ] Return source CV filenames with each answer
- [ ] `backend/app.py`: FastAPI `/chat` endpoint

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
