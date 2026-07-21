from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService


class RAGService:
    @staticmethod
    def retrieve_context(query: str, n_results: int = 5) -> list:
        """
        Retrieve relevant document chunks for a query.
        Returns list of (chunk_text, metadata) tuples.
        """
        query_embedding = EmbeddingService.embed_text(query)
        results = VectorStoreService.search(query_embedding, n_results=n_results)
        
        if not results or not results.get('documents'):
            return []
        
        retrieved = []
        for i in range(len(results['documents'][0])):
            chunk_text = results['documents'][0][i]
            metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
            retrieved.append({
                'text': chunk_text,
                'metadata': metadata
            })
        
        return retrieved
