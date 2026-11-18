import requests

from nexus import config

# The providers a visitor can pick in the web app, with their own API key
VISITOR_PROVIDERS = ["gemini", "anthropic", "openai"]

PROVIDER_LABELS = {
    "gemini": "Gemini",
    "anthropic": "Claude",
    "openai": "OpenAI",
    "ollama": "Ollama",
}


def default_model(provider_name):
    if provider_name == "gemini":
        return config.GEMINI_MODEL
    if provider_name == "anthropic":
        return config.ANTHROPIC_MODEL
    if provider_name == "openai":
        return config.OPENAI_MODEL
    return config.OLLAMA_MODEL


def make_llm(provider_name, api_key="", model=""):
    """Build a client for one provider. An empty key or model means the one from .env."""
    # Each SDK is imported only when it is used, so the server stays small in memory
    if provider_name == "gemini":
        from nexus.llm.gemini_client import GeminiClient
        return GeminiClient(api_key, model)
    if provider_name == "anthropic":
        from nexus.llm.anthropic_client import AnthropicClient
        return AnthropicClient(api_key, model)
    if provider_name == "openai":
        from nexus.llm.openai_client import OpenAIClient
        return OpenAIClient(api_key, model)
    if provider_name == "ollama":
        from nexus.llm.ollama_client import OllamaClient
        return OllamaClient(model)
    raise ValueError("Unknown provider '" + provider_name + "'. Use one of: gemini, anthropic, openai, ollama.")


def pick_provider_name():
    """The server's own model: the one in LLM_PROVIDER, or the first provider with a key in .env.

    "none" means the server has no model of its own. Questions then get search results only,
    unless the visitor brings their own key.
    """
    if config.LLM_PROVIDER:
        if config.LLM_PROVIDER != "none" and config.LLM_PROVIDER not in PROVIDER_LABELS:
            raise ValueError(
                "Unknown LLM_PROVIDER '" + config.LLM_PROVIDER + "'. "
                "Use one of: gemini, anthropic, openai, ollama, none."
            )
        return config.LLM_PROVIDER

    if config.GEMINI_API_KEY:
        return "gemini"
    if config.ANTHROPIC_API_KEY:
        return "anthropic"
    if config.OPENAI_API_KEY:
        return "openai"
    # No key at all: use Ollama if it runs on this machine, otherwise search only
    if ollama_is_running():
        return "ollama"
    return "none"


def ollama_is_running():
    try:
        requests.get(config.OLLAMA_URL + "/api/tags", timeout=1)
        return True
    except requests.RequestException:
        return False


_llm = None


def get_llm():
    """The server's own model, or None when it has none."""
    global _llm
    if _llm is None:
        provider_name = pick_provider_name()
        if provider_name == "none":
            return None
        _llm = make_llm(provider_name)
    return _llm


def require_llm():
    """For commands that cannot work without a model, like evals with answers."""
    llm = get_llm()
    if llm is None:
        raise RuntimeError("No model is set up. Add an API key to .env, or start Ollama.")
    return llm
