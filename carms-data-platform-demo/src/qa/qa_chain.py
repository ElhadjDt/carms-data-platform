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


def build_qa_chain():
    vectorstore = load_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

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


_qa_chain = None


def _get_chain():
    """Lazy-load the QA chain on first call so importing this module doesn't trigger provider setup."""
    global _qa_chain
    if _qa_chain is None:
        _qa_chain = build_qa_chain()
    return _qa_chain


def ask(question: str) -> str:
    return _get_chain().invoke(question)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    answer = ask("What are the selection criteria for the Family Medicine program at McGill?")
    logger.info("Answer: %s", answer)
