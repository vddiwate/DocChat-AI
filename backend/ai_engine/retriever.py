"""Document retrieval module supporting similarity and MMR search strategies."""
from typing import List

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from backend.core.config import CONFIG
from backend.core.logger import get_logger

logger = get_logger("ai_engine.retriever")


class RAGRetriever:
    def __init__(self, vectorstore: FAISS):
        """Initializes the retriever with a valid FAISS vector store."""
        if vectorstore is None:
            error_msg = "Cannot initialize RAGRetriever with a None vectorstore."
            logger.error(error_msg)
            raise ValueError(error_msg)

        self.vectorstore = vectorstore

    def get_similarity_retriever(self, k: int = None):
        """Returns a standard cosine similarity retriever."""
        top_k = k or CONFIG.DEFAULT_TOP_K
        logger.info(f"Creating similarity retriever with k={top_k}")
        return self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": top_k}
        )

    def get_mmr_retriever(self, k: int = None, lambda_mult: float = None):
        """Returns a Maximal Marginal Relevance retriever for diverse search."""
        top_k = k or CONFIG.DEFAULT_TOP_K
        l_mult = lambda_mult if lambda_mult is not None else CONFIG.MMR_LAMBDA_MULT
        logger.info(f"Creating MMR retriever with k={top_k}, lambda_mult={l_mult}")
        return self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": top_k, "lambda_mult": l_mult}
        )

    def get_retriever(self, search_type: str = None, k: int = None):
        """Factory method returning the configured retriever strategy."""
        stype = (search_type or CONFIG.DEFAULT_SEARCH_TYPE).lower()
        if stype == "mmr":
            return self.get_mmr_retriever(k=k)
        return self.get_similarity_retriever(k=k)

    def retrieve(self, query: str, search_type: str = None, k: int = None) -> List[Document]:
        """Executes document retrieval for a given query string."""
        if not query or not query.strip():
            logger.warning("Empty query provided for retrieval.")
            return []

        try:
            logger.info(f"Retrieving documents for query: '{query}'")
            retriever_instance = self.get_retriever(search_type=search_type, k=k)
            documents = retriever_instance.invoke(query)
            logger.info(f"Retrieved {len(documents)} document(s).")
            return documents

        except Exception as e:
            logger.exception(f"Error during retrieval for query '{query}': {e}")
            raise RuntimeError(f"Retrieval error: {e}") from e
