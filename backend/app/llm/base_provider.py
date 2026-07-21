from abc import ABC, abstractmethod
from typing import List, Dict, Any


class LLMProvider(ABC):
    name: str = 'base'

    @property
    def provider_name(self) -> str:
        return self.name

    @abstractmethod
    def generate_test_cases(
        self,
        feature_name: str,
        query: str,
        retrieved_context: List[Dict[str, Any]],
        test_types: List[str],
        num_cases: int,
    ) -> List[Dict[str, Any]]:
        """Generate structured test cases from retrieved context."""
        raise NotImplementedError()
