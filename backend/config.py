"""Shared config + embedding helpers for the RAG pipeline."""
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

CVS_DIR = ROOT / "data" / "cvs"
CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION = "cvs"

CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-5.4-mini")
EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. OpenAI returns unit-normalized vectors."""
    out: list[list[float]] = []
    for i in range(0, len(texts), 100):  # batch to stay within request limits
        resp = client.embeddings.create(model=EMBED_MODEL, input=texts[i:i + 100])
        out.extend(d.embedding for d in resp.data)
    return out


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
