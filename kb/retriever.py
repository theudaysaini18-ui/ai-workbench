import chromadb
from chromadb.utils import embedding_functions
import os

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
client = chromadb.PersistentClient(path=CHROMA_PATH)
embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="BAAI/bge-small-en-v1.5")
collection = client.get_or_create_collection("sop_kb", embedding_function=embed_fn)


def search_kb(query: str, top_k: int = 5) -> list[dict]:
    """Searches the local vector store and returns grounded, cited chunks."""
    res = collection.query(query_texts=[query], n_results=top_k)
    if not res["documents"] or not res["documents"][0]:
        return []
    return [
        {"text": doc, "source": meta["source"], "score": dist}
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]


if __name__ == "__main__":
    results = search_kb("pressure limit for boiler inspection")
    for r in results:
        print(r["source"], "->", r["text"][:100])