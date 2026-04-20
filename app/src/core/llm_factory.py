"""
llm_factory.py
==============
Single source of truth for all LLM providers.
Switch by setting PROVIDER= in your .env file.

Your original code used:
  - gemini-2.0-flash-001  →  orchestrator (chats.send_message)
  - gemini-2.5-flash      →  code-gen sub-LLM (text_to_sql)

After migration:
  - get_llm()         →  orchestrator (AgentExecutor)
  - get_codegen_llm() →  code-gen sub-LLM (text_to_sql replacement)

Supported PROVIDER values:
  google | openai | azure_openai | anthropic | groq | mistral | ollama | huggingface
"""

import os
from functools import lru_cache
from langchain_core.language_models import BaseChatModel



# ── Provider loaders ──────────────────────────────────────────────────────────

def _load_google() -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=os.environ["_ACTIVE_MODEL"],
        temperature=float(os.getenv("TEMPERATURE", 0.1)),
        google_api_key=os.getenv("GOOGLE_API_KEY",""),
        convert_system_message_to_human=True,   # Gemini quirk
    )


def _load_openai() -> BaseChatModel:
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=os.environ["_ACTIVE_MODEL"],
        temperature=float(os.getenv("TEMPERATURE", 0.1)),
    )


def _load_azure_openai() -> BaseChatModel:
    from langchain_openai import AzureChatOpenAI
    return AzureChatOpenAI(
        azure_deployment=os.environ["_ACTIVE_MODEL"],
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        temperature=float(os.getenv("TEMPERATURE", 0.1)),
    )


def _load_anthropic() -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        model=os.environ["_ACTIVE_MODEL"],
        temperature=float(os.getenv("TEMPERATURE", 0.1)),
    )


def _load_groq() -> BaseChatModel:
    # SLMs tuned for tool calling: llama3-groq-8b-8192-tool-use-preview
    from langchain_groq import ChatGroq
    return ChatGroq(
        model=os.environ["_ACTIVE_MODEL"],
        temperature=float(os.getenv("TEMPERATURE", 0.1)),
        groq_api_key=os.getenv("GROQ_API_KEY"),
    )


def _load_mistral() -> BaseChatModel:
    from langchain_mistralai import ChatMistralAI
    return ChatMistralAI(
        model=os.environ["_ACTIVE_MODEL"],
        temperature=float(os.getenv("TEMPERATURE", 0.1)),
        mistral_api_key=os.getenv("MISTRAL_API_KEY"),
    )


def _load_ollama() -> BaseChatModel:
    # Local SLMs with good tool calling: llama3.1 | phi4 | qwen2.5
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=os.environ["_ACTIVE_MODEL"],
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=float(os.getenv("TEMPERATURE", 0.1)),
    )


def _load_huggingface() -> BaseChatModel:
    from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
    pipeline = HuggingFacePipeline.from_model_id(
        model_id=os.environ["_ACTIVE_MODEL"],
        task="text-generation",
        pipeline_kwargs={"max_new_tokens": 2048, "temperature": 0.1, "do_sample": True},
    )
    return ChatHuggingFace(llm=pipeline)


_PROVIDERS: dict[str, callable] = {
    "google":       _load_google,
    "openai":       _load_openai,
    "azure_openai": _load_azure_openai,
    "anthropic":    _load_anthropic,
    "groq":         _load_groq,
    "mistral":      _load_mistral,
    "ollama":       _load_ollama,
    "huggingface":  _load_huggingface,
}

# ── Default model names per provider ─────────────────────────────────────────

_DEFAULT_ORCHESTRATOR = {
    "google":       "gemini-2.0-flash-001",
    "openai":       "gpt-4o",
    "azure_openai": "gpt-4o",
    "anthropic":    "claude-3-5-sonnet-20241022",
    "groq":         "llama3-groq-8b-8192-tool-use-preview",
    "mistral":      "mistral-small-latest",
    "ollama":       "llama3.1",
    "huggingface":  "microsoft/Phi-3-mini-4k-instruct",
}

_DEFAULT_CODEGEN = {
    "google":       "gemini-2.5-flash",   # matches your original text_to_sql model
    "openai":       "gpt-4o-mini",
    "azure_openai": "gpt-4o-mini",
    "anthropic":    "claude-3-haiku-20240307",
    "groq":         "llama-3.1-8b-instant",
    "mistral":      "open-mistral-7b",
    "ollama":       "llama3.1",
    "huggingface":  "microsoft/Phi-3-mini-4k-instruct",
}


# ── Internal helper ───────────────────────────────────────────────────────────

def _build_llm(model_name: str) -> BaseChatModel:
    provider = os.getenv("PROVIDER", "google").lower().strip()
    loader = _PROVIDERS.get(provider)
    if not loader:
        raise ValueError(f"Unknown PROVIDER='{provider}'. Supported: {list(_PROVIDERS)}")
    os.environ["_ACTIVE_MODEL"] = model_name
    llm = loader()
    del os.environ["_ACTIVE_MODEL"]
    return llm


# ── Public API ────────────────────────────────────────────────────────────────


def get_llm() -> BaseChatModel:
    """
    Orchestrator LLM — used by AgentExecutor for tool routing.
    Equivalent to your original gemini-2.0-flash-001 chats session.
    """
    provider = os.getenv("PROVIDER", "google").lower().strip()
    model = os.getenv("ORCHESTRATOR_MODEL", _DEFAULT_ORCHESTRATOR.get(provider, ""))
    print(f"[LLM Factory] Orchestrator: provider={provider}, model={model}")
    return _build_llm(model)



def get_codegen_llm() -> BaseChatModel:
    """
    Code-generation LLM — used inside the sql tool for text_to_sql.
    Equivalent to your original gemini-2.5-flash generate_content call.
    Can be a different (smarter/faster) model than the orchestrator.
    """
    provider =  "google"
    model = os.getenv("CODEGEN_MODEL", _DEFAULT_CODEGEN.get(provider, ""))
    print(f"[LLM Factory] Codegen: provider={provider}, model={model}")
    return _build_llm(model)


def get_provider_info() -> dict:
    provider = os.getenv("PROVIDER", "google").lower().strip()
    return {
        "provider": provider,
        "orchestrator_model": os.getenv("ORCHESTRATOR_MODEL", _DEFAULT_ORCHESTRATOR.get(provider)),
        "codegen_model": os.getenv("CODEGEN_MODEL", _DEFAULT_CODEGEN.get(provider)),
    }