from typing import List
from langchain_huggingface import HuggingFaceEmbeddings
import os

class EmbeddingService:
    def __init__(self):
        # Using a small, fast local model that doesn't require an API key
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.embeddings = HuggingFaceEmbeddings(model_name=self.model_name)

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generates a vector embedding for the given text using a local HuggingFace model.
        Returns a list of floats (dimension 384).
        """
        return self.embeddings.embed_query(text)

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self.embeddings.embed_documents(texts)
