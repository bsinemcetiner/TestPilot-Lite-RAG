from typing import List, Dict, Any
from app.llm.base_provider import LLMProvider


class FoundryLocalProvider(LLMProvider):
    def __init__(self):
        raise NotImplementedError('Foundry local provider is not implemented yet.')

    def generate_test_cases(
        self,
        feature_name: str,
        query: str,
        retrieved_context: List[Dict[str, Any]],
        test_types: List[str],
        num_cases: int,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError('Foundry local provider is not implemented yet.')
