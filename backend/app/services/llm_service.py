import logging
from typing import List, Dict, Any, Tuple

from app.llm.provider_factory import LLMProviderFactory
from app.llm.mock_provider import MockLLMProvider

logger = logging.getLogger(__name__)


class LLMService:
    @staticmethod
    def generate_test_cases(
        feature_name: str,
        query: str,
        retrieved_context: List[Dict[str, Any]],
        test_types: List[str],
        num_cases: int,
        provider_name: str = 'mock',
    ) -> Tuple[List[Dict[str, Any]], str]:
        provider = LLMProviderFactory.get_provider(provider_name)

        try:
            cases = provider.generate_test_cases(
                feature_name=feature_name,
                query=query,
                retrieved_context=retrieved_context,
                test_types=test_types,
                num_cases=num_cases,
            )
            return cases, provider.provider_name
        except Exception as exc:
            logger.warning(
                "LLM provider failed (%s): %s. Falling back to mock provider.",
                provider.provider_name,
                str(exc),
            )
            fallback = MockLLMProvider()
            return fallback.generate_test_cases(
                feature_name=feature_name,
                query=query,
                retrieved_context=retrieved_context,
                test_types=test_types,
                num_cases=num_cases,
            ), fallback.provider_name
