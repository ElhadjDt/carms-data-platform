"""
RAG QA chain: load FAISS index, retriever + LLM to answer questions from program descriptions.
LLM and embedding providers are selected via LLM_PROVIDER / EMBEDDING_PROVIDER env vars.
"""
import logging

from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from src.config import settings
from src.qa.providers import get_embeddings, get_llm

logger = logging.getLogger(__name__)


def load_vectorstore():
    """Load FAISS vector store from configured path using the active embedding provider."""
    return FAISS.load_local(
        settings.FAISS_PATH,
        get_embeddings(),
        allow_dangerous_deserialization=True,
    )


def build_qa_chain(retriever):
    prompt = ChatPromptTemplate.from_template(
        """You are a helpful assistant answering questions about residency programs.

Use ONLY the following context to answer the question.
If the answer is not in the context, say you don't know.

Context:
{context}

Question:
{question}
"""
    )

    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | get_llm()
        | StrOutputParser()
    )

    return rag_chain


_retriever = None
_qa_chain = None


def initialize():
    """Pre-build the retriever and QA chain at app startup so requests never trigger a cold build."""
    global _retriever, _qa_chain
    _retriever = load_vectorstore().as_retriever(search_kwargs={"k": 5})
    _qa_chain = build_qa_chain(_retriever)


def _get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = load_vectorstore().as_retriever(search_kwargs={"k": 5})
    return _retriever


def _get_chain():
    """Return the pre-built chain, or build it on first call if initialize() was not called."""
    global _qa_chain
    if _qa_chain is None:
        _qa_chain = build_qa_chain(_get_retriever())
    return _qa_chain


def ask(question: str) -> dict:
    """Answer the question and return distinct program sources cited in the
    retrieved context, so callers can link back to the real CaRMS program pages."""
    answer = _get_chain().invoke(question)

    sources = []
    seen_urls = set()
    for doc in _get_retriever().invoke(question):
        url = doc.metadata.get("program_url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            sources.append(
                {"program_name": doc.metadata.get("program_name"), "program_url": url}
            )

    return {"answer": answer, "sources": sources}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = ask("What are the selection criteria for the Family Medicine program at McGill?")
    logger.info("Answer: %s", result["answer"])
    logger.info("Sources: %s", result["sources"])
