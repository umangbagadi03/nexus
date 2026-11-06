from nexus import config
from nexus.llm.anthropic_client import AnthropicClient
from nexus.llm.gemini_client import GeminiClient
from nexus.llm.ollama_client import OllamaClient
from nexus.llm.openai_client import OpenAIClient

PROVIDERS = {
    "gemini": GeminiClient,
    "anthropic": AnthropicClient,
    "openai": OpenAIClient,
    "ollama": OllamaClient,
}


def pick_provider_name():
    # An explicit choice in .env always wins
    if config.LLM_PROVIDER:
        if config.LLM_PROVIDER not in PROVIDERS:
            raise ValueError(
                "Unknown LLM_PROVIDER '" + config.LLM_PROVIDER + "'. "
                "Use one of: gemini, anthropic, openai, ollama."
            )
        return config.LLM_PROVIDER

    # Otherwise use the first provider that has an API key.
    # Ollama runs locally and needs no key, so it is the fallback.
    if config.GEMINI_API_KEY:
        return "gemini"
    if config.ANTHROPIC_API_KEY:
        return "anthropic"
    if config.OPENAI_API_KEY:
        return "openai"
    return "ollama"


_llm = None


def get_llm():
    global _llm
    if _llm is None:
        provider_name = pick_provider_name()
        client_class = PROVIDERS[provider_name]
        _llm = client_class()
    return _llm
