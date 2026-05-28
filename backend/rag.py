"""Retrieval-augmented answering over the CV collection.

embed query -> similarity search in Chroma -> grounded OpenAI answer (streamed) + sources.
"""
from collections.abc import Iterator

import chromadb

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


def _context_and_sources(question: str, top_k: int) -> tuple[str, list[str]]:
    coll = _collection()
    res = coll.query(query_embeddings=[embed_query(question)], n_results=top_k)
    docs = res["documents"][0]
    sources = [m["source"] for m in res["metadatas"][0]]
    context = "\n\n".join(
        f"--- CV: {src} ---\n{doc}" for src, doc in zip(sources, docs))
    return f"CONTEXT (retrieved CVs):\n{context}\n\nQUESTION: {question}", sources


def stream(question: str, top_k: int = TOP_K) -> Iterator[tuple[str, object]]:
    """Yield ("token", delta) as the answer streams, then ("sources", [cited files])."""
    user, sources = _context_and_sources(question, top_k)
    parts: list[str] = []
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        stream=True,
    )
    for chunk in resp:
        delta = chunk.choices[0].delta.content
        if delta:
            parts.append(delta)
            yield "token", delta
    # Sources can only be resolved once the full answer exists (cited filenames).
    full = "".join(parts)
    yield "sources", [s for s in sources if s in full]


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "Who has experience with Python?"
    print("Q:", q, "\n")
    cited: list[str] = []
    for kind, payload in stream(q):
        if kind == "token":
            print(payload, end="", flush=True)
        else:
            cited = payload  # type: ignore[assignment]
    print("\n\nSources:", ", ".join(cited))
