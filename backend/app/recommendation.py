"""Recommendation engine - uses LLM + Vector DB to generate personalized suggestions"""

from typing import List

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate

from app.config import settings
from app.user_profile import UserProfile


class RecommendationEngine:
    """AI-powered recommendation engine"""

    def __init__(self):
        # TODO: Initialize embeddings and vector store
        self.embeddings = None
        self.vector_store = None
        self.llm = None

    async def initialize(self):
        """Initialize embeddings and vector store"""
        if not settings.openai_api_key:
            print("Warning: OpenAI API key not set. Recommendations will be mock.")
            return

        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)

        # TODO: Load or create FAISS vector store
        # self.vector_store = FAISS.load_local("data/attractions.faiss", self.embeddings)

        # Initialize LLM for recommendations
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            openai_api_key=settings.openai_api_key,
        )

    async def get_recommendations(
        self, user_profile: UserProfile, limit: int = 10
    ) -> List[dict]:
        """Get personalized recommendations based on user profile"""
        # TODO: Implement vector search + LLM ranking
        # Placeholder mock recommendations
        return [
            {
                "id": "1",
                "name": "The Ruins",
                "type": "historical",
                "description": "A beautiful ruined mansion with Italian architecture",
                "personality_match_score": 0.85,
            },
            {
                "id": "2",
                "name": "Masskara Festival",
                "type": "cultural",
                "description": "Annual festival celebrating Bacolod's smiling culture",
                "personality_match_score": 0.92,
            },
        ]

