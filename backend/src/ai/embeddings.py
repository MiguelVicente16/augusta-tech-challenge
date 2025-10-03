"""
Simplified embedding service using LangChain.
Replaces the custom EmbeddingService with ~20 lines.
"""

from langchain_openai import OpenAIEmbeddings
from typing import List
import os

class EmbeddingService:
    """Simple wrapper around LangChain OpenAI embeddings."""

    def __init__(self, model: str = "text-embedding-3-small"):
        """Initialize with OpenAI API key from environment."""
        self.embeddings = OpenAIEmbeddings(
            model=model,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return await self.embeddings.aembed_query(text)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batching handled by LangChain)."""
        return await self.embeddings.aembed_documents(texts)
