from app.config import LLM_PROVIDER
from app.services.llm import anthropic_provider, ollama_provider, openai_provider

_PROVIDERS = {
    "anthropic": anthropic_provider,
    "openai": openai_provider,
    "ollama": ollama_provider,
}


def get_provider():
    provider = _PROVIDERS.get(LLM_PROVIDER)
    if provider is None:
        raise RuntimeError(f"Unknown LLM_PROVIDER '{LLM_PROVIDER}'. Choose one of {list(_PROVIDERS)}.")
    return provider
