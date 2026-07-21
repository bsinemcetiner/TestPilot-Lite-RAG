import os
from typing import Any, Dict, List

try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency fallback
    np = None

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except Exception:  # pragma: no cover - optional dependency fallback
    chromadb = None
    ChromaSettings = None


class VectorStoreService:
    _client = None
    _collection = None
    _fallback_store: List[Dict[str, Any]] = []

    @classmethod
    def get_client(cls):
        if cls._client is None:
            if chromadb is None:
                cls._fallback_store = []
                return None

            persist_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../../chroma_data")
            )
            os.makedirs(persist_dir, exist_ok=True)

            cls._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(
                    anonymized_telemetry=False
                ),
            )

        return cls._client

    @classmethod
    def get_collection(cls):
        if cls._collection is None:
            client = cls.get_client()
            if client is None:
                cls._collection = None
            else:
                cls._collection = client.get_or_create_collection(
                    name="documents",
                    metadata={"hnsw:space": "cosine"}
                )
        return cls._collection

    @classmethod
    def add_chunks(cls, doc_id: int, chunks: list, embeddings: list, metadata_list: list):
        """Add document chunks to vector database."""
        collection = cls.get_collection()
        if collection is not None:
            ids = [f"doc_{doc_id}_chunk_{i}" for i in range(len(chunks))]
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadata_list
            )
            return

        for i, chunk in enumerate(chunks):
            cls._fallback_store.append({
                "id": f"doc_{doc_id}_chunk_{i}",
                "document_id": doc_id,
                "document": chunk,
                "embedding": embeddings[i] if i < len(embeddings) else [],
                "metadata": metadata_list[i] if i < len(metadata_list) else {},
            })

    @classmethod
    def search(cls, query_embedding, n_results: int = 5):
        """Search for similar chunks."""
        collection = cls.get_collection()
        if collection is not None:
            return collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )

        if not cls._fallback_store:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        query_vector = cls._to_vector(query_embedding)
        ranked = []
        for item in cls._fallback_store:
            score = cls._cosine_similarity(query_vector, cls._to_vector(item["embedding"]))
            ranked.append((score, item))

        ranked.sort(key=lambda entry: entry[0], reverse=True)
        top_items = ranked[:n_results]

        return {
            "documents": [[item["document"] for _, item in top_items]],
            "metadatas": [[item["metadata"] for _, item in top_items]],
            "distances": [[max(0.0, 1.0 - score) for score, _ in top_items]],
        }

    @classmethod
    def delete_document_chunks(cls, doc_id: int):
        """Delete all chunks for a document."""
        collection = cls.get_collection()
        if collection is not None:
            where_filter = {"document_id": {"$eq": doc_id}}
            collection.delete(where=where_filter)
            return

        cls._fallback_store = [item for item in cls._fallback_store if item.get("document_id") != doc_id]

    @staticmethod
    def _to_vector(value):
        if np is not None:
            return np.array(value, dtype=float)
        return list(value)

    @staticmethod
    def _cosine_similarity(a, b):
        if np is not None:
            a_arr = np.array(a, dtype=float)
            b_arr = np.array(b, dtype=float)
            if np.linalg.norm(a_arr) == 0 or np.linalg.norm(b_arr) == 0:
                return 0.0
            return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))

        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
