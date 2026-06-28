"""
Provider factory for LLM and embeddings.
Controls which backend is used via LLM_PROVIDER and EMBEDDING_PROVIDER env vars.
Supported values: 'openai' (default) | 'ollama'

Adding a new provider: implement the two if-blocks below and add its package to requirements.
All model names and URLs are configured in src.config — no defaults live here.
"""
import os

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from src.config import settings


def get_llm() -> BaseChatModel:
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set. Set it or switch LLM_PROVIDER=ollama.")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=settings.OPENAI_LLM_MODEL, temperature=0)
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=settings.OLLAMA_LLM_MODEL, base_url=settings.OLLAMA_HOST, temperature=0)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}. Choose 'openai' or 'ollama'.")


def get_embeddings() -> Embeddings:
    provider = settings.EMBEDDING_PROVIDER.lower()
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set. Set it or switch EMBEDDING_PROVIDER=ollama.")
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model=settings.OPENAI_EMBEDDING_MODEL)
    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(model=settings.OLLAMA_EMBEDDING_MODEL, base_url=settings.OLLAMA_HOST)
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider!r}. Choose 'openai' or 'ollama'.")
