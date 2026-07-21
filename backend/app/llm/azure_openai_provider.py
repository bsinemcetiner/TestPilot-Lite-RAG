import os
from typing import List, Dict, Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from app.llm.base_provider import LLMProvider


class AzureOpenAIProvider(LLMProvider):
    name = 'azure_openai'

    def __init__(self):
        if OpenAI is None:
            raise ImportError('openai package is not installed')

        self.client = OpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            base_url=os.getenv('AZURE_OPENAI_ENDPOINT'),
        )

    def generate_test_cases(
        self,
        feature_name: str,
        query: str,
        retrieved_context: List[Dict[str, Any]],
        test_types: List[str],
        num_cases: int,
    ) -> List[Dict[str, Any]]:
        system_prompt = (
            'You are a software test generation assistant. Generate structured JSON test cases ' 
            'based on the feature description and retrieved project context. The output must be valid JSON ' 
            'matching the provided schema.'
        )

        context_text = '\n\n'.join(
            [f"[{i+1}] {item['metadata'].get('document_name', 'Unknown')}: {item['text']}" for i, item in enumerate(retrieved_context)]
        )

        prompt = (
            f"Feature: {feature_name}\n"
            f"Query: {query}\n"
            f"Retrieved Context:\n{context_text}\n\n"
            f"Generate {num_cases} test cases in JSON format with fields: title, type, priority, "
            "preconditions, steps, expected_result, source_references, confidence. "
            "Each source_reference should include document_name, chunk_id, and quote."
        )

        response = self.client.responses.create(
            model=os.getenv('AZURE_OPENAI_MODEL', 'gpt-4o-mini'),
            input=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ],
            max_output_tokens=1000,
        )

        text = self._extract_response_text(response)
        return self._parse_response(text)

    def _extract_response_text(self, response: Any) -> str:
        if hasattr(response, 'output_text') and response.output_text:
            return response.output_text

        if hasattr(response, 'output'):
            output = getattr(response, 'output')
            if isinstance(output, list) and len(output) > 0:
                item = output[0]
                if isinstance(item, dict):
                    return item.get('content', '') or item.get('text', '') or ''

        if hasattr(response, 'choices') and len(response.choices) > 0:
            choice = response.choices[0]
            if hasattr(choice, 'text') and choice.text:
                return choice.text
            if hasattr(choice, 'message'):
                message = choice.message
                if isinstance(message, dict):
                    return message.get('content', '') or ''

        return str(response)

    def _parse_response(self, text: str) -> List[Dict[str, Any]]:
        import json

        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        raise ValueError('Azure OpenAI provider returned invalid JSON response')
