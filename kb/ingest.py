import chromadb
from chromadb.utils import embedding_functions
import fitz  # PyMuPDF
import os

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
client = chromadb.PersistentClient(path=CHROMA_PATH)
embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="BAAI/bge-small-en-v1.5")
collection = client.get_or_create_collection("sop_kb", embedding_function=embed_fn)


def extract_text(path: str) -> str:
    if path.lower().endswith(".pdf"):
        doc = fitz.open(path)
        return "\n".join(page.get_text() for page in doc)
    with open(path, "r", errors="ignore") as f:
        return f.read()


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 100) -> list[str]:
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start = end - overlap
    return [c for c in chunks if c.strip()]


def ingest_document(path: str, doc_id: str = None) -> str:
    doc_id = doc_id or os.path.basename(path)
    text = extract_text(path)
    chunks = chunk_text(text)
    collection.add(
        documents=chunks,
        ids=[f"{doc_id}_{i}" for i in range(len(chunks))],
        metadatas=[{"source": doc_id, "chunk": i} for i in range(len(chunks))],
    )
    return f"Ingested {len(chunks)} chunks from {doc_id}"


def ingest_folder(folder: str):
    for fname in os.listdir(folder):
        full_path = os.path.join(folder, fname)
        if os.path.isfile(full_path):
            print(ingest_document(full_path))


if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else "data/sample_sops"
    ingest_folder(folder)