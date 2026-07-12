"""
Application configuration: database URL, data paths, and FAISS index path.
All paths can be overridden via environment variables for Docker and AWS deployments.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project root: carms-data-platform-demo/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Default data dir: sibling of carms-data-platform-demo (repo_root/data)
_DEFAULT_DATA_DIR = _PROJECT_ROOT.parent / "data"


class Settings:
    """Centralized settings for database, data directories, and RAG vector store."""

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://carms:carms@localhost:5432/carms_db",
    )

    # Base directories for raw data, extracted files, and embeddings
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(_DEFAULT_DATA_DIR))).resolve()
    RAW_DIR: Path = DATA_DIR / "raw"
    EXTRACTED_DIR: Path = DATA_DIR / "extracted"
    EMBEDDINGS_DIR: Path = DATA_DIR / "embeddings"
    FAISS_PATH: Path = Path(
        os.getenv("FAISS_PATH", str(EMBEDDINGS_DIR / "faiss_index"))
    ).resolve()

    # ETL source files
    DISCIPLINE_EXCEL: Path = RAW_DIR / "1503_discipline.xlsx"
    PROGRAM_MASTER_EXCEL: Path = RAW_DIR / "1503_program_master.xlsx"
    PROGRAM_DESCRIPTIONS_CSV: Path = EXTRACTED_DIR / "1503_program_descriptions_x_section.csv"

    # RAG provider configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "openai")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_LLM_MODEL: str = os.getenv("OLLAMA_LLM_MODEL", "llama3.2:1b")
    OLLAMA_EMBEDDING_MODEL: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "all-minilm:l6")
    OPENAI_LLM_MODEL: str = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


settings = Settings()