import asyncio
from typing import List

import structlog
from sentence_transformers import SentenceTransformer

logger = structlog.get_logger()


class EmbeddingClient:
    """
    Local embedding utility (A3).
    Uses sentence-transformers/all-MiniLM-L6-v2 (384 dimensions).
    """

    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            logger.info("loading_embedding_model", model="all-MiniLM-L6-v2")
            cls._model = SentenceTransformer("all-MiniLM-L6-v2")
        return cls._model

    async def embed(self, text: str) -> List[float]:
        """
        Generates a 384-dim vector for the given text.
        Runs in a threadpool to avoid blocking the event loop.
        """
        model = self.get_model()
        loop = asyncio.get_event_loop()
        # model.encode is a blocking CPU-bound task
        embedding = await loop.run_in_executor(None, model.encode, text)
        return embedding.tolist()


# Singleton instance
embedding_client = EmbeddingClient()
