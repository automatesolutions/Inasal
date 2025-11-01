"""RAG engine - RAG pipeline to fetch real-time data (weather, events, local tips)"""

from typing import List, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from app.config import settings


class RAGEngine:
    """Retrieval-Augmented Generation engine for real-time data enrichment"""

    def __init__(self):
        self.llm = None
        if settings.openai_api_key:
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.5,
                openai_api_key=settings.openai_api_key,
            )

    async def get_weather_info(self, location: str = "Bacolod, Philippines") -> dict:
        """Get weather information - TODO: integrate weather API"""
        # Placeholder
        return {
            "location": location,
            "temperature": 28,
            "condition": "Partly Cloudy",
            "updated_at": datetime.utcnow().isoformat(),
        }

    async def get_local_events(self, date: Optional[str] = None) -> List[dict]:
        """Get local events - TODO: integrate events API or scraping"""
        # Placeholder
        return [
            {
                "id": "1",
                "title": "Masskara Festival",
                "date": "2025-10-19",
                "location": "Bacolod City",
                "description": "Annual festival celebration",
            }
        ]

    async def get_local_tips(self, query: str) -> str:
        """Get local tips using RAG"""
        # TODO: Implement RAG pipeline with vector search + LLM
        if not self.llm:
            return "Local tips unavailable - API key not configured."

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a friendly local guide from Bacolod, Philippines. "
                    "Provide helpful, authentic tips about Bacolod in a warm, welcoming tone.",
                ),
                ("human", "{query}"),
            ]
        )

        chain = prompt | self.llm
        response = await chain.ainvoke({"query": query})
        return response.content

