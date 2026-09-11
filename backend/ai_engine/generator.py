"""Generation module connecting retriever, prompt templates, and Groq LLM using LCEL."""
from typing import Generator, List

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_groq import ChatGroq

from backend.ai_engine.prompt import RAG_PROMPT
from backend.core.config import CONFIG
from backend.core.logger import get_logger

load_dotenv()

logger = get_logger("ai_engine.generator")


class RAGGenerator:
    def __init__(
        self,
        retriever,
        model_name: str = None,
        temperature: float = None
    ):
        """Initializes the generator with retriever, Groq LLM, and prompt template."""
        if retriever is None:
            error_msg = "Cannot initialize RAGGenerator without a valid retriever instance."
            logger.error(error_msg)
            raise ValueError(error_msg)

        self.retriever = retriever
        self.model_name = model_name or CONFIG.GROQ_MODEL_NAME
        self.temperature = temperature if temperature is not None else CONFIG.LLM_TEMPERATURE

        self._llm = self._initialize_llm()
        self._prompt = RAG_PROMPT
        self._chain = self._build_lcel_chain()

    def _initialize_llm(self) -> ChatGroq:
        """Initializes and returns the ChatGroq model instance."""
        try:
            logger.info(f"Initializing ChatGroq (model='{self.model_name}', temperature={self.temperature})")
            return ChatGroq(model=self.model_name, temperature=self.temperature)
        except Exception as e:
            logger.exception(f"Failed to initialize ChatGroq: {e}")
            raise RuntimeError(f"LLM initialization error: {e}") from e

    def format_docs(self, docs: List[Document]) -> str:
        """Concatenates list of retrieved Document objects into a single context string."""
        if not docs:
            return ""
        return "\n\n".join(doc.page_content for doc in docs)

    def _build_lcel_chain(self):
        """Constructs the LangChain Expression Language (LCEL) execution chain."""
        try:
            logger.info("Building LCEL RAG execution chain...")
            rag_chain = (
                {"context": self.retriever | self.format_docs, "question": RunnablePassthrough()}
                | self._prompt
                | self._llm
                | StrOutputParser()
            )
            logger.info("LCEL RAG chain constructed successfully.")
            return rag_chain

        except Exception as e:
            logger.exception(f"Error while constructing LCEL RAG chain: {e}")
            raise RuntimeError(f"Failed to build RAG chain: {e}") from e

    def generate_answer(self, query: str) -> str:
        """Generates an answer for a user query using the RAG execution chain."""
        if not query or not query.strip():
            error_msg = "Query cannot be empty."
            logger.warning(error_msg)
            return error_msg

        try:
            logger.info(f"Generating answer for query: '{query}'")
            response = self._chain.invoke(query)
            logger.info("Answer generated successfully.")
            return response

        except Exception as e:
            logger.exception(f"Error during response generation for query '{query}': {e}")
            raise RuntimeError(f"Generation error: {e}") from e

    def stream_answer(self, query: str) -> Generator[str, None, None]:
        """Streams generated answer tokens progressively for a user query."""
        if not query or not query.strip():
            error_msg = "Query cannot be empty."
            logger.warning(error_msg)
            yield error_msg
            return

        try:
            logger.info(f"Streaming answer for query: '{query}'")
            for chunk in self._chain.stream(query):
                yield chunk
            logger.info("Answer streaming completed successfully.")

        except Exception as e:
            logger.exception(f"Error during streaming for query '{query}': {e}")
            yield f"\n\n[Error generating stream: {e}]"
