# AI-Powered CV Screener

A chat application for screening résumés. Ask natural-language questions about a
collection of CVs and get answers grounded in their content, with the source CVs cited.

Built as a Retrieval-Augmented Generation (RAG) pipeline:

1. **CV Generation** — 25–30 realistic fake CVs (PDF, with AI-generated photos).
2. **RAG Workflow** — extract → chunk → embed → store → retrieve, grounded on the CVs only.
3. **Chat Interface** — a clean web UI to ask questions and see the answer + source CVs.

---

## Architecture

```mermaid
flowchart LR
    subgraph gen["1 · CV Generation (offline)"]
        G1[Gemini<br/>profile text] --> G3[HTML/Jinja<br/>template]
        G2[Gemini image<br/>AI headshot] --> G3
        G3 --> PDF[(data/cvs/*.pdf)]
    end

    subgraph ingest["2 · Ingestion (offline)"]
        PDF --> EX[Extract text<br/>pypdf] --> EM[Embed<br/>gemini-embedding-001] --> VDB[(Chroma<br/>vector store)]
    end

    subgraph serve["3 · Query (runtime)"]
        UI[React chat UI] -->|question| API[FastAPI /chat]
        API --> QE[Embed question] --> RET[Similarity search] --> VDB
        VDB --> CTX[Top-k CV chunks] --> LLM[Gemini<br/>grounded answer]
        LLM -->|answer + source CVs| UI
    end
```

## Tech stack

| Layer        | Choice                                  | Why |
|--------------|-----------------------------------------|-----|
| LLM + embeddings | Google AI Studio — `gemini-2.5-flash` + `gemini-embedding-001` | Free tier, one key covers chat + embeddings, GCP-aligned |
| Vector store | Chroma (local, embedded)                | Zero external accounts, runs fully locally |
| Backend      | Python + FastAPI                        | Clean RAG service, easy to read |
| Frontend     | React + Vite + TypeScript + Tailwind    | Simple, fast chat UI |
| CV photos    | Google AI Studio — `gemini-3.1-flash-image-preview` (fallback: OpenAI `gpt-image-2`) | Unique AI headshot per candidate, inferred from name/role/location; auto-fails over if Gemini errors |

**Production swaps** (not built here to keep the prototype focused): the vector
store can be swapped for **Pinecone/Weaviate**, the query path wrapped in a
**LangGraph** agent, and traced with **Langfuse**.

---

## Screenshots

| Chat interface | A generated CV |
|---|---|
| ![Chat UI](docs/ui.png) | ![Sample CV](docs/sample_cv.png) |

Answers are grounded in the CVs and cite the source files actually used.

---

## Quick start

> Requires Python 3.12+, Node 20+, and a free [Google AI Studio key](https://aistudio.google.com/apikey).

```bash
cp .env.example .env        # add your GEMINI_API_KEY
```

**1. Generate CVs**

```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python ../scripts/generate_cvs.py     # writes data/cvs/*.pdf
```

**2. Ingest into the vector store**

```bash
python ingest.py                      # builds backend/chroma_db/
```

**3. Run the backend**

```bash
uvicorn app:app --reload --port 8000
```

**4. Run the frontend**

```bash
cd ../frontend && npm install && npm run dev   # http://localhost:5173
```

## Sample questions

- "Who has experience with Python?"
- "Which candidate graduated from UPC?"
- "Summarize the profile of Jane Doe."

---

## Project layout

```
scripts/generate_cvs.py       # CV generation (text + AI photo + PDF)
scripts/regenerate_photos.py  # re-shoot photos for existing profiles (no text re-gen)
backend/
  app.py                  # FastAPI /chat endpoint
  ingest.py               # PDF -> chunks -> embeddings -> Chroma
  rag.py                  # retrieval + grounded generation
  requirements.txt
frontend/                 # React + Vite chat UI
data/cvs/                 # generated PDFs (gitignored)
docs/                     # diagram source / notes
```
