"""Retrieval-augmented answering over the CV collection.

embed query -> similarity search in Chroma -> grounded Gemini answer + sources.
"""
import chromadb
from google.genai import types

from config import CHAT_MODEL, CHROMA_DIR, COLLECTION, client, embed_query

TOP_K = 12

SYSTEM_PROMPT = """You are a recruiting assistant that answers questions about a set of \
candidate CVs. Use ONLY the CV excerpts provided in the context to answer.

Rules:
- Base every statement strictly on the provided CVs. Do not invent facts.
- If the answer is not in the CVs, say so plainly.
- When naming candidates, use their name and cite the source file in parentheses, e.g. "Jane Doe (jane_doe.pdf)".
- For "who has..." questions, list every matching candidate you find in the context.
- Be concise and well structured."""

_coll = None


def _collection():
    global _coll
    if _coll is None:
        chroma = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _coll = chroma.get_collection(COLLECTION)
    return _coll


def answer(question: str, top_k: int = TOP_K) -> dict:
    coll = _collection()
    res = coll.query(query_embeddings=[embed_query(question)], n_results=top_k)
    docs = res["documents"][0]
    sources = [m["source"] for m in res["metadatas"][0]]

    context = "\n\n".join(
        f"--- CV: {src} ---\n{doc}" for src, doc in zip(sources, docs))
    prompt = f"{SYSTEM_PROMPT}\n\nCONTEXT (retrieved CVs):\n{context}\n\nQUESTION: {question}"

    resp = client.models.generate_content(
        model=CHAT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2),
    )
    text = resp.text.strip()
    # Report the CVs actually cited in the answer (not just everything retrieved).
    cited = [s for s in sources if s in text]
    return {"answer": text, "sources": cited}


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "Who has experience with Python?"
    out = answer(q)
    print("Q:", q, "\n")
    print(out["answer"])
    print("\nSources consulted:", ", ".join(out["sources"]))
