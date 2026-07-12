"""
Build FAISS vector store from ProgramDocument table for RAG retrieval.
Embedding provider is selected via EMBEDDING_PROVIDER env var ('openai' | 'ollama').
"""
import logging
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlmodel import Session, select

from src.config import settings
from src.db.models import Program, ProgramDocument
from src.db.session import engine
from src.qa.providers import get_embeddings

load_dotenv()

logger = logging.getLogger(__name__)


def load_documents() -> List[dict]:
    """Load all ProgramDocument rows from the database, joined with their
    parent Program for name/URL so citations don't need a DB lookup at query time."""
    with Session(engine) as session:
        rows = session.exec(
            select(ProgramDocument, Program).join(
                Program, ProgramDocument.program_id == Program.program_id
            )
        ).all()

    documents = [
        {
            "id": doc.id,
            "program_id": doc.program_id,
            "section_name": doc.section_name,
            "content": doc.content,
            "program_name": program.program_name,
            "program_url": program.program_url,
        }
        for doc, program in rows
    ]
    logger.info("Loaded %d documents from ProgramDocument.", len(documents))
    return documents


def chunk_documents(documents: List[dict]):
    """Split documents into chunks for embedding.

    chunk_size/overlap are sized for this dataset's section-level content
    (avg. ~2.6k chars/section): most sections split into 1-2 chunks rather
    than the many small fragments a 500-char chunk_size would produce,
    which keeps local (CPU-only) embedding time reasonable.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
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
                    "program_name": doc["program_name"],
                    "program_url": doc["program_url"],
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
    if settings.EMBEDDING_PROVIDER.lower() == "openai" and not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set. Set it or switch EMBEDDING_PROVIDER=ollama.")
    documents = load_documents()
    chunks = chunk_documents(documents)
    build_vectorstore(chunks)


if __name__ == "__main__":
    build_embeddings_pipeline()
