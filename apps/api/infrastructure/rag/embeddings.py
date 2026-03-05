from typing import List
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    
    class Config:
        env_file = ".env"

settings = Settings()

class EmbeddingService:
    def __init__(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=settings.GEMINI_API_KEY
        )

    def generate_embedding(self, text: str) -> List[float]:
        # Clean text slightly before embedding
        cleaned_text = text.replace("\n", " ")
        return self.embeddings.embed_query(cleaned_text)

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self.embeddings.embed_documents(texts)
