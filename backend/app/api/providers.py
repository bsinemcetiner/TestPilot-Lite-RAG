from fastapi import APIRouter
from app.llm.provider_factory import LLMProviderFactory
import os

router = APIRouter()


@router.get("/providers")
def get_providers():
    """Return the configured and supported LLM providers."""
    available = LLMProviderFactory.get_available_providers()
    active = os.getenv('LLM_PROVIDER', 'mock').lower()
    default = 'mock'

    return {
        'available_providers': available,
        'active_provider': active,
        'default_provider': default,
    }
