"""Shared config + embedding helpers for the RAG pipeline."""
import math
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

CVS_DIR = ROOT / "data" / "cvs"
CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION = "cvs"

CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")
EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def _normalize(vec: list[float]) -> list[float]:
    # Gemini embeddings need normalizing when output_dimensionality != 3072.
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def embed_texts(texts: list[str], task_type: str) -> list[list[float]]:
    """Embed a batch of texts. task_type is RETRIEVAL_DOCUMENT or RETRIEVAL_QUERY."""
    out: list[list[float]] = []
    for i in range(0, len(texts), 20):  # batch to stay within request limits
        batch = texts[i:i + 20]
        resp = client.models.embed_content(
            model=EMBED_MODEL,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type=task_type, output_dimensionality=EMBED_DIM),
        )
        out.extend(_normalize(e.values) for e in resp.embeddings)
    return out


def embed_query(text: str) -> list[float]:
    return embed_texts([text], task_type="RETRIEVAL_QUERY")[0]
