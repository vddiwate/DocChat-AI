"""Prompt templates for context and question injection in DocChat."""
from langchain_core.prompts import ChatPromptTemplate

RAG_PROMPT_TEMPLATE = """You are a helpful and precise assistant. Use the following context to answer the question.
If the answer cannot be found in the context, state that you do not know based on the provided context.

Context:
{context}

Question:
{question}

Answer:"""

RAG_PROMPT = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
