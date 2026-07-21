import os
from typing import List, Optional

from app.llm.mock_provider import MockLLMProvider


class LLMProviderFactory:
    @staticmethod
    def get_provider(provider_name: str = None) -> Optional[object]:
        env_provider = os.getenv('LLM_PROVIDER', 'mock').lower()
        provider_name = (provider_name or env_provider or 'mock').lower()

        if provider_name == 'mock':
            return MockLLMProvider()

        if provider_name == 'openai':
            try:
                from app.llm.openai_provider import OpenAIProvider
                return OpenAIProvider()
            except Exception:
                return MockLLMProvider()

        if provider_name == 'azure_openai':
            try:
                from app.llm.azure_openai_provider import AzureOpenAIProvider
                return AzureOpenAIProvider()
            except Exception:
                return MockLLMProvider()

        if provider_name == 'ollama':
            try:
                from app.llm.ollama_provider import OllamaProvider
                return OllamaProvider()
            except Exception:
                return MockLLMProvider()

        if provider_name == 'foundry_local':
            try:
                from app.llm.foundry_local_provider import FoundryLocalProvider
                return FoundryLocalProvider()
            except Exception:
                return MockLLMProvider()

        return MockLLMProvider()

    @staticmethod
    def get_available_providers() -> List[str]:
        return ['mock', 'openai', 'azure_openai', 'ollama', 'foundry_local']
