try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency fallback
    np = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional dependency fallback
    SentenceTransformer = None


class EmbeddingService:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            if SentenceTransformer is None:
                cls._model = None
            else:
                cls._model = SentenceTransformer('all-MiniLM-L6-v2')
        return cls._model

    @classmethod
    def embed_text(cls, text: str):
        """Generate embedding for a single text."""
        model = cls.get_model()
        if model is not None:
            return model.encode(text, convert_to_numpy=True)
        return cls._fallback_embedding(text)

    @classmethod
    def embed_batch(cls, texts: list):
        """Generate embeddings for multiple texts."""
        model = cls.get_model()
        if model is not None:
            return model.encode(texts, convert_to_numpy=True)
        return [cls._fallback_embedding(text) for text in texts]

    @staticmethod
    def _fallback_embedding(text: str):
        tokens = [token.lower() for token in text.replace('\n', ' ').split() if token]
        vector = [0.0] * 8
        if not tokens:
            return vector

        for i, token in enumerate(tokens[:8]):
            vector[i % 8] += len(token)

        if np is not None:
            return np.array(vector, dtype=float).tolist()
        return vector
