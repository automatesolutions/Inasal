"""Recommendation engine - uses LLM + Vector DB to generate personalized suggestions"""

import json
import os
from typing import List, Optional, Dict
from pathlib import Path

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate
from langchain.schema import Document

from app.config import settings
from app.user_profile import UserProfile, PersonalityTraits, UserPreferences
from app.prompts import (
    RECOMMENDATION_SYSTEM_PROMPT,
    RECOMMENDATION_USER_PROMPT,
    HIDDEN_GEMS_PROMPT,
)


class RecommendationEngine:
    """AI-powered recommendation engine with vector search"""

    def __init__(self):
        self.embeddings = None
        self.vector_store: Optional[FAISS] = None
        self.llm = None
        self.attractions_data: List[Dict] = []

    async def initialize(self):
        """Initialize embeddings and vector store"""
        if not settings.openai_api_key:
            print("Warning: OpenAI API key not set. Recommendations will use mock data.")
            return

        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key,
        )

        # Initialize LLM for recommendations
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.7,
            openai_api_key=settings.openai_api_key,
        )

        # Load attractions data
        await self._load_attractions_data()

        # Load or create vector store
        await self._initialize_vector_store()

    async def _load_attractions_data(self):
        """Load attractions data from JSON file"""
        data_file = Path(__file__).parent.parent / "data" / "attractions.json"
        if data_file.exists():
            with open(data_file, "r", encoding="utf-8") as f:
                self.attractions_data = json.load(f)
        else:
            print(f"Warning: Attractions data file not found at {data_file}")
            self.attractions_data = []

    async def _initialize_vector_store(self):
        """Initialize FAISS vector store"""
        if not self.embeddings:
            return

        store_path = Path(settings.vector_store_path)
        store_path.parent.mkdir(parents=True, exist_ok=True)

        # Create documents from attractions
        documents = []
        for attraction in self.attractions_data:
            # Create searchable text combining name, description, and tags
            text = f"{attraction.get('name', '')}\n{attraction.get('description', '')}\n"
            text += " ".join(attraction.get('tags', []))
            
            metadata = {
                "id": attraction.get("id"),
                "name": attraction.get("name"),
                "type": attraction.get("type"),
                "tags": ", ".join(attraction.get("tags", [])),
            }
            
            documents.append(Document(page_content=text, metadata=metadata))

        if not documents:
            print("Warning: No documents to index. Using mock recommendations.")
            return

        # Check if vector store exists
        if store_path.exists() and list(store_path.glob("*.faiss")):
            try:
                # Load existing vector store
                self.vector_store = FAISS.load_local(
                    str(store_path), self.embeddings, allow_dangerous_deserialization=True
                )
                print(f"✅ Loaded existing vector store from {store_path}")
            except Exception as e:
                print(f"Error loading vector store: {e}. Creating new one.")
                self.vector_store = None

        if not self.vector_store:
            # Create new vector store
            try:
                self.vector_store = FAISS.from_documents(documents, self.embeddings)
                self.vector_store.save_local(str(store_path))
                print(f"✅ Created and saved vector store to {store_path}")
            except Exception as e:
                print(f"Error creating vector store: {e}")
                self.vector_store = None

    def _calculate_personality_score(
        self, attraction: Dict, personality: PersonalityTraits
    ) -> float:
        """Calculate personality match score for an attraction"""
        if "personality_match" not in attraction:
            return 0.5  # Default score

        match_scores = attraction["personality_match"]
        weights = {
            "adventurous": personality.adventurous,
            "cultural": personality.cultural,
            "foodie": personality.foodie,
            "nature_lover": personality.nature_lover,
            "history_buff": personality.history_buff,
            "social": personality.social,
        }

        total_score = 0.0
        total_weight = 0.0

        for trait, weight in weights.items():
            if trait in match_scores:
                trait_score = match_scores[trait]
                total_score += trait_score * weight
                total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.5

    async def _get_recommendations_from_llm(
        self,
        user_profile: UserProfile,
        retrieved_attractions: List[Dict],
        limit: int = 10,
    ) -> List[Dict]:
        """Use LLM to generate personalized recommendations"""
        if not self.llm or not retrieved_attractions:
            return retrieved_attractions[:limit]

        # Format attractions for prompt
        attractions_text = "\n\n".join(
            [
                f"{idx + 1}. {att['name']} ({att['type']})\n"
                f"   {att['description'][:200]}...\n"
                f"   Tags: {', '.join(att.get('tags', []))}"
                for idx, att in enumerate(retrieved_attractions)
            ]
        )

        # Create prompts
        system_prompt = RECOMMENDATION_SYSTEM_PROMPT.format(
            adventurous=user_profile.personality.adventurous,
            cultural=user_profile.personality.cultural,
            foodie=user_profile.personality.foodie,
            nature_lover=user_profile.personality.nature_lover,
            history_buff=user_profile.personality.history_buff,
            social=user_profile.personality.social,
            budget_range=user_profile.preferences.budget_range or "not specified",
            travel_style=user_profile.preferences.travel_style or "not specified",
            interests=", ".join(user_profile.preferences.interests) or "none specified",
        )

        user_prompt = RECOMMENDATION_USER_PROMPT.format(
            count=len(retrieved_attractions),
            attractions=attractions_text,
            limit=limit,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", user_prompt),
            ]
        )

        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({})
            
            # Parse LLM response and return original attractions (enhanced with LLM reasoning)
            # For now, return ranked attractions with personality scores
            return self._rank_by_personality(retrieved_attractions, user_profile, limit)
        except Exception as e:
            print(f"Error in LLM recommendation: {e}")
            return self._rank_by_personality(retrieved_attractions, user_profile, limit)

    def _rank_by_personality(
        self, attractions: List[Dict], profile: UserProfile, limit: int
    ) -> List[Dict]:
        """Rank attractions by personality match score"""
        scored = []
        for att in attractions:
            score = self._calculate_personality_score(att, profile.personality)
            att_with_score = att.copy()
            att_with_score["personality_match_score"] = score
            scored.append(att_with_score)

        # Sort by score descending
        scored.sort(key=lambda x: x["personality_match_score"], reverse=True)
        return scored[:limit]

    async def get_recommendations(
        self, user_profile: UserProfile, query: Optional[str] = None, limit: int = 10
    ) -> List[Dict]:
        """Get personalized recommendations based on user profile"""
        if limit > settings.max_recommendation_limit:
            limit = settings.max_recommendation_limit

        # If vector store is not available, return mock recommendations
        if not self.vector_store:
            return self._get_mock_recommendations(user_profile, limit)

        try:
            # Build search query based on user interests
            search_query = query or self._build_query_from_profile(user_profile)

            # Perform vector search
            results = self.vector_store.similarity_search_with_score(
                search_query, k=limit * 2
            )

            # Map results back to attractions
            retrieved_attractions = []
            for doc, score in results:
                attraction_id = doc.metadata.get("id")
                attraction = next(
                    (
                        att
                        for att in self.attractions_data
                        if str(att.get("id")) == str(attraction_id)
                    ),
                    None,
                )
                if attraction:
                    attraction["similarity_score"] = float(score)
                    retrieved_attractions.append(attraction)

            # Use LLM to refine and rank recommendations
            recommendations = await self._get_recommendations_from_llm(
                user_profile, retrieved_attractions, limit
            )

            return recommendations

        except Exception as e:
            print(f"Error in recommendation retrieval: {e}")
            return self._get_mock_recommendations(user_profile, limit)

    def _build_query_from_profile(self, profile: UserProfile) -> str:
        """Build search query from user profile"""
        query_parts = []

        # Add interests
        if profile.preferences.interests:
            query_parts.extend(profile.preferences.interests)

        # Add personality-based keywords
        if profile.personality.foodie > 0.7:
            query_parts.append("food restaurants local cuisine")
        if profile.personality.history_buff > 0.7:
            query_parts.append("historical museum heritage")
        if profile.personality.nature_lover > 0.7:
            query_parts.append("nature outdoor hiking waterfalls")
        if profile.personality.cultural > 0.7:
            query_parts.append("cultural festival traditions")
        if profile.personality.adventurous > 0.7:
            query_parts.append("adventure activities")

        return " ".join(query_parts) if query_parts else "Bacolod attractions tourism"

    async def get_hidden_gems(
        self, user_profile: UserProfile, limit: int = 5
    ) -> List[Dict]:
        """Get hidden gems based on user profile"""
        # For hidden gems, look for attractions with lower popularity but high personality match
        all_recommendations = await self.get_recommendations(user_profile, limit=20)
        
        # Filter for less common types or tags
        hidden_gems = [
            att for att in all_recommendations
            if att.get("type") in ["cultural", "historical", "food"]
            and att.get("personality_match_score", 0) > 0.7
        ]
        
        return hidden_gems[:limit]

    def _get_mock_recommendations(
        self, user_profile: UserProfile, limit: int
    ) -> List[Dict]:
        """Return mock recommendations when vector store is unavailable"""
        if not self.attractions_data:
            return [
                {
                    "id": "1",
                    "name": "The Ruins",
                    "type": "historical",
                    "description": "A beautiful ruined mansion with Italian architecture",
                    "personality_match_score": 0.85,
                }
            ]

        return self._rank_by_personality(self.attractions_data, user_profile, limit)


# Global recommendation engine instance
recommendation_engine = RecommendationEngine()
