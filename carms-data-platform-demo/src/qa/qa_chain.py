"""
RAG QA chain: load FAISS index, retriever + LLM to answer questions from program descriptions.
LLM and embedding providers are selected via LLM_PROVIDER / EMBEDDING_PROVIDER env vars.
"""
import logging
import re

from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from src.config import settings
from src.qa.providers import get_embeddings, get_llm

logger = logging.getLogger(__name__)

# Small instruction-tuned models (e.g. llama3.2:1b) don't reliably follow a
# "don't say according to the context" system instruction on longer/denser
# context, so strip this filler deterministically wherever it slips through.
_PREAMBLE_RE = re.compile(
    r"\b(according to|based on)\s+the\s+(provided\s+)?(context|information)\b[,:]?\s*",
    re.IGNORECASE,
)


def _strip_meta_commentary(answer: str) -> str:
    cleaned = _PREAMBLE_RE.sub("", answer).strip()
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def load_vectorstore():
    """Load FAISS vector store from configured path using the active embedding provider."""
    return FAISS.load_local(
        settings.FAISS_PATH,
        get_embeddings(),
        allow_dangerous_deserialization=True,
    )


def build_qa_chain(retriever):
    # Split into system/human messages rather than one templated block: smaller
    # instruction-tuned models (e.g. llama3.2:1b) follow style rules like "don't
    # say 'according to the context'" much more reliably in the system message
    # than when it's mixed into the same block as the context/question.
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You answer questions about residency programs using only the given "
                "context. Answer directly and naturally, as if you simply know these "
                "facts. Never mention the words 'context', 'information', or "
                "'provided' in your answer. If the answer isn't in the context, say "
                "you don't know.",
            ),
            ("human", "Context:\n{context}\n\nQuestion:\n{question}"),
        ]
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
    answer = _strip_meta_commentary(_get_chain().invoke(question))

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
