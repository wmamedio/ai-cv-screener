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

## 3. Chat Interface  ✅
- [x] React + Vite + TS + Tailwind chat page
- [x] Text input + answer display + source CVs shown (markdown rendering)
- [x] Wire to `/chat` (Vite dev proxy → :8000)
- [x] Sources reflect CVs actually cited in the answer

## Deliverable wrap-up
- [x] Full stack verified end-to-end in a real browser (Playwright screenshots)
- [x] Architecture diagram (README, Mermaid) — overview-diagram deliverable
- [x] Sample questions work (Python → 11 candidates / UPC → 2 / Jane Doe summary)
- [x] Grounding negative test (out-of-scope question → "not in CVs")
- [x] Screenshots added to README
- [ ] (User) Record 3–10 min Loom demo + code walkthrough

## Review
- Stack: Gemini (2.5-flash + embedding-001) · Chroma · FastAPI · React/Vite/Tailwind.
- 28 CVs generated as PDFs with AI photos; seeded facts make the demo questions land.
- RAG grounds strictly on retrieved CVs and cites sources; verified in browser.
- Kept lean per scope: no LangGraph/Pinecone/Langfuse build (noted as production swaps).
- Remaining: user records the demo video.
