"""
RAG QA chain: load FAISS index, retriever + LLM to answer questions from program descriptions.
Uses configurable FAISS_PATH from src.config for Docker and AWS deployments.
"""
import logging

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from src.config import settings

load_dotenv()


def load_vectorstore():
    """Load FAISS vector store from configured path."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return FAISS.load_local(
        settings.FAISS_PATH,
        embeddings,
        allow_dangerous_deserialization=True,
    )


def build_qa_chain():
    vectorstore = load_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )

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
        {
            "context": retriever,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain


QA_CHAIN = build_qa_chain()


def ask(question: str) -> str:
    return QA_CHAIN.invoke(question)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    answer = ask("What are the selection criteria for the Family Medicine program at McGill?")
    logger.info("Answer: %s", answer)