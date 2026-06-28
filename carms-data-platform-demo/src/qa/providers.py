"""
Provider factory for LLM and embeddings.
Controls which backend is used via LLM_PROVIDER and EMBEDDING_PROVIDER env vars.
Supported values: 'openai' (default) | 'ollama'

Adding a new provider: implement the two if-blocks below and add its package to requirements.
"""
import os

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel


def get_llm() -> BaseChatModel:
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini"),
            temperature=0,
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=os.getenv("OLLAMA_LLM_MODEL", "llama3.2:1b"),
            base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            temperature=0,
        )
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}. Choose 'openai' or 'ollama'.")


def get_embeddings() -> Embeddings:
    provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        )
    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(
            model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:v1.5"),
            base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        )
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider!r}. Choose 'openai' or 'ollama'.")
