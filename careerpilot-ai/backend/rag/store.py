"""
RAG layer for CareerPilot AI.

Stores the user's personal documents (resume, project descriptions,
past cover letters, interview notes, etc.) in a ChromaDB collection
per-user, and exposes retrieval for grounding agent outputs.
"""
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
from backend.core.config import get_settings
from backend.core.llm import get_embeddings

settings = get_settings()


class PersonalDocStore:
    """Thin wrapper around a per-user Chroma collection."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=f"user_{user_id}_docs"
        )
        self._embeddings = None

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = get_embeddings()
        return self._embeddings

    def add_documents(self, docs: List[Dict[str, Any]]):
        """docs: [{id, text, metadata}]"""
        if not docs:
            return
        texts = [d["text"] for d in docs]
        ids = [d["id"] for d in docs]
        metadatas = [d.get("metadata", {}) for d in docs]
        vectors = self.embeddings.embed_documents(texts)
        self.collection.upsert(
            ids=ids, documents=texts, metadatas=metadatas, embeddings=vectors
        )

    def query(self, query_text: str, n_results: int = 5) -> List[str]:
        """Return top-n relevant document chunks for a query."""
        if self.collection.count() == 0:
            return []
        vector = self.embeddings.embed_query(query_text)
        results = self.collection.query(query_embeddings=[vector], n_results=n_results)
        docs = results.get("documents", [[]])
        return docs[0] if docs else []
