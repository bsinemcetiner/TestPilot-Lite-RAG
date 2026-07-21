import os
from typing import List, Dict, Any

try:
    import requests
except ImportError:
    requests = None

from app.llm.base_provider import LLMProvider


class OllamaProvider(LLMProvider):
    name = 'ollama'

    def __init__(self):
        if requests is None:
            raise ImportError('requests package is not installed')

        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'llama2')

    def generate_test_cases(
        self,
        feature_name: str,
        query: str,
        retrieved_context: List[Dict[str, Any]],
        test_types: List[str],
        num_cases: int,
    ) -> List[Dict[str, Any]]:
        context_text = '\n\n'.join(
            [f"[{i+1}] {item['metadata'].get('document_name', 'Unknown')}: {item['text']}" for i, item in enumerate(retrieved_context)]
        )

        prompt = (
            f"You are a test generation assistant. Generate {num_cases} structured JSON test cases for the feature '{feature_name}' using the retrieved context below. "
            f"Respond only with valid JSON. Output fields: title, type, priority, preconditions, steps, expected_result, source_references, confidence. "
            f"Each source_reference should include document_name, chunk_id, quote.\n\n"
            f"Retrieved Context:\n{context_text}\n\n"
            f"Query: {query}"
        )

        url = f"{self.base_url}/api/models/{self.model}/outputs"
        response = requests.post(url, json={
            'prompt': prompt,
            'max_tokens': 1000,
            'temperature': 0.2,
        })
        response.raise_for_status()

        data = response.json()
        text = data.get('output', '')
        return self._parse_response(text)

    def _parse_response(self, text: str) -> List[Dict[str, Any]]:
        import json

        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        raise ValueError('Ollama provider returned invalid JSON response')
