"""Ingest CV PDFs into a Chroma vector store.

For each PDF: extract text -> embed (one vector per CV) -> store with the
filename as the source. CVs are ~1 page, so a whole-CV chunk keeps retrieval
simple and makes source attribution exact (1 vector = 1 candidate).

Usage:  python ingest.py
"""
import shutil

import chromadb
from pypdf import PdfReader

from config import CHROMA_DIR, COLLECTION, CVS_DIR, embed_texts


def extract_text(pdf_path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def main():
    pdfs = sorted(CVS_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs in {CVS_DIR}. Run scripts/generate_cvs.py first.")

    print(f"Extracting text from {len(pdfs)} CVs...")
    sources = [p.name for p in pdfs]
    docs = [extract_text(p) for p in pdfs]

    print(f"Embedding {len(docs)} CVs...")
    vectors = embed_texts(docs, task_type="RETRIEVAL_DOCUMENT")

    # Rebuild the collection from scratch for a clean, idempotent ingest.
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    chroma = chromadb.PersistentClient(path=str(CHROMA_DIR))
    coll = chroma.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    coll.add(
        ids=sources,
        embeddings=vectors,
        documents=docs,
        metadatas=[{"source": s} for s in sources],
    )
    print(f"Ingested {coll.count()} CVs into Chroma at {CHROMA_DIR.name}/")


if __name__ == "__main__":
    main()
