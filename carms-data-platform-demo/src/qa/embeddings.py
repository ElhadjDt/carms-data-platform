"""
Build FAISS vector store from ProgramDocument table for RAG retrieval.
Embedding provider is selected via EMBEDDING_PROVIDER env var ('openai' | 'ollama').
"""
import logging
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlmodel import Session, select

from src.config import settings
from src.db.models import ProgramDocument
from src.db.session import engine
from src.qa.providers import get_embeddings

load_dotenv()

logger = logging.getLogger(__name__)


def load_documents() -> List[dict]:
    """Load all ProgramDocument rows from the database."""
    with Session(engine) as session:
        rows = session.exec(select(ProgramDocument)).all()

    documents = [
        {
            "id": row.id,
            "program_id": row.program_id,
            "section_name": row.section_name,
            "content": row.content,
        }
        for row in rows
    ]
    logger.info("Loaded %d documents from ProgramDocument.", len(documents))
    return documents


def chunk_documents(documents: List[dict]):
    """Split documents into chunks for embedding."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " ", ""],
    )

    chunks = []
    for doc in documents:
        sub_docs = splitter.create_documents(
            texts=[doc["content"]],
            metadatas=[
                {
                    "program_id": doc["program_id"],
                    "section_name": doc["section_name"],
                    "source_id": doc["id"],
                }
            ],
        )
        chunks.extend(sub_docs)

    logger.info("Created %d text chunks.", len(chunks))
    return chunks


def build_vectorstore(chunks, persist_path: str | None = None):
    """Embed chunks and save FAISS index to disk."""
    path = persist_path or settings.FAISS_PATH
    vectorstore = FAISS.from_documents(chunks, get_embeddings())
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(path)
    logger.info("FAISS vector store saved to: %s", path)
    return vectorstore


def load_vectorstore(persist_path: str | None = None):
    """Load an existing FAISS index from disk."""
    path = persist_path or settings.FAISS_PATH
    vectorstore = FAISS.load_local(
        path,
        get_embeddings(),
        allow_dangerous_deserialization=True,
    )
    logger.info("FAISS vector store loaded from: %s", path)
    return vectorstore


def build_embeddings_pipeline():
    """Full pipeline: load documents → chunk → embed → save FAISS index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    build_vectorstore(chunks)


if __name__ == "__main__":
    build_embeddings_pipeline()
