"""Recommendation engine - uses LLM + Vector DB to generate personalized suggestions"""

import json
import os
import re
from typing import List, Optional, Dict
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate
from langchain.schema import Document

from app.config import settings
from app.user_profile import UserProfile, PersonalityTraits, UserPreferences
from app.llm_factory import get_chat_llm, get_embeddings
from app.prompts import (
    RECOMMENDATION_SYSTEM_PROMPT,
    RECOMMENDATION_USER_PROMPT,
    HIDDEN_GEMS_PROMPT,
    TRAIT_MAPPING_PROMPT,
    CONTEXT_INJECTION_PROMPT,
    RECOMMENDATION_GENERATION_PROMPT,
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
        # Skip if already initialized
        if self.attractions_data and (self.llm or self.vector_store is not None):
            return
        
        # Initialize LLM using factory (supports Ollama, OpenAI, Groq)
        if not self.llm:
            self.llm = get_chat_llm(temperature=0.7)
        
        if not self.llm:
            print("⚠️  Warning: LLM not available. Recommendations will use mock data.")
            print(f"   Provider: {settings.llm_provider}")
            print("   Tip: Install Ollama (ollama.ai) or set OPENAI_API_KEY/GROQ_API_KEY")

        # Initialize embeddings using factory (optional - only needed for vector search)
        if not self.embeddings:
            try:
                self.embeddings = get_embeddings()
            except Exception as e:
                print(f"ℹ️  Could not initialize embeddings: {e}")
                print("   Using LLM-only recommendations (no vector search).")
                self.embeddings = None
        
        if not self.embeddings:
            print("ℹ️  Embeddings not available. Using LLM-only recommendations (no vector search).")
            print("   This is fine - recommendations will work using LLM filtering instead.")

        # Load attractions data
        if not self.attractions_data:
            await self._load_attractions_data()

        # Load or create vector store (only if embeddings available)
        if self.embeddings and not self.vector_store:
            try:
                await self._initialize_vector_store()
            except Exception as e:
                print(f"⚠️  Could not initialize vector store: {e}")
                print("   Continuing with LLM-only recommendations.")
                self.vector_store = None

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
                error_str = str(e)
                # Check if it's a quota error
                if "quota" in error_str.lower() or "429" in error_str or "insufficient_quota" in error_str:
                    print(f"⚠️  OpenAI quota exceeded while creating vector store. Using mock recommendations.")
                    print(f"   Error: {e}")
                    print(f"   Tip: Vector store will be created once quota is available.")
                else:
                    print(f"⚠️  Error creating vector store: {e}")
                    print(f"   Using mock recommendations until vector store is available.")
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
            
            # Parse LLM response to extract recommendations
            content = response.content if hasattr(response, "content") else str(response)
            recommendations = self._parse_llm_recommendations(
                content, retrieved_attractions, user_profile, limit
            )
            
            if recommendations:
                return recommendations
            else:
                # Fallback to personality-based ranking
                return self._rank_by_personality(retrieved_attractions, user_profile, limit)
        except Exception as e:
            print(f"Error in LLM recommendation: {e}")
            return self._rank_by_personality(retrieved_attractions, user_profile, limit)

    def _parse_llm_recommendations(
        self, 
        llm_response: str, 
        available_attractions: List[Dict], 
        profile: UserProfile,
        limit: int
    ) -> List[Dict]:
        """Parse LLM response to extract and rank recommended attractions"""
        recommendations = []
        
        # Create a lookup map for attractions by name (case-insensitive)
        attraction_map = {}
        for att in available_attractions:
            name_lower = att.get("name", "").lower()
            attraction_map[name_lower] = att
            # Also try partial matches
            for word in name_lower.split():
                if len(word) > 3:  # Only meaningful words
                    if word not in attraction_map:
                        attraction_map[word] = att
        
        # Try to find attraction names in LLM response
        llm_lower = llm_response.lower()
        found_attractions = {}
        
        for name_lower, attraction in attraction_map.items():
            if name_lower in llm_lower:
                if attraction.get("id") not in found_attractions:
                    found_attractions[attraction.get("id")] = attraction.copy()
                    # Calculate personality score
                    score = self._calculate_personality_score(attraction, profile.personality)
                    found_attractions[attraction.get("id")]["personality_match_score"] = score
                    # Try to extract explanation from LLM response
                    found_attractions[attraction.get("id")]["llm_explanation"] = self._extract_explanation(
                        llm_response, attraction.get("name", "")
                    )
        
        # Sort by personality score and return
        recommendations = list(found_attractions.values())
        recommendations.sort(key=lambda x: x.get("personality_match_score", 0), reverse=True)
        
        # If we found some, return them; otherwise return empty to trigger fallback
        return recommendations[:limit] if recommendations else []
    
    def _extract_explanation(self, llm_response: str, attraction_name: str) -> str:
        """Extract explanation for an attraction from LLM response"""
        # Try to find the section about this attraction
        lines = llm_response.split("\n")
        explanation_parts = []
        capturing = False
        
        for i, line in enumerate(lines):
            if attraction_name.lower() in line.lower():
                capturing = True
                explanation_parts.append(line.strip())
            elif capturing:
                if line.strip() and not line.strip().startswith(("-", "•", "1.", "2.", "3.")):
                    explanation_parts.append(line.strip())
                elif line.strip().startswith(("-", "•", "1.", "2.", "3.")):
                    break
        
        explanation = " ".join(explanation_parts[:3])  # Take first 3 relevant lines
        return explanation[:200] if explanation else ""  # Limit length
    
    def _rank_by_personality(
        self, attractions: List[Dict], profile: UserProfile, limit: int
    ) -> List[Dict]:
        """Rank attractions by personality match score with enhanced logic"""
        scored = []
        for att in attractions:
            score = self._calculate_personality_score(att, profile.personality)
            att_with_score = att.copy()
            att_with_score["personality_match_score"] = score
            
            # Add personalized explanation based on personality match
            att_with_score["why_recommended"] = self._generate_why_recommended(
                att, profile.personality, score
            )
            
            scored.append(att_with_score)

        # Sort by score descending, with tie-breaking by type diversity
        scored.sort(key=lambda x: (
            x["personality_match_score"], 
            -len(x.get("tags", []))  # Prefer attractions with more tags
        ), reverse=True)
        
        # Ensure diversity in types
        return self._ensure_diversity(scored[:limit * 2], limit)
    
    def _generate_why_recommended(
        self, attraction: Dict, personality: PersonalityTraits, score: float
    ) -> str:
        """Generate a personalized explanation for why this attraction is recommended"""
        reasons = []
        
        if "personality_match" in attraction:
            match_scores = attraction["personality_match"]
            
            # Find top matching traits
            trait_scores = [
                (trait, match_scores.get(trait, 0), getattr(personality, trait, 0))
                for trait in ["adventurous", "cultural", "foodie", "nature_lover", "history_buff", "social"]
            ]
            trait_scores.sort(key=lambda x: x[1] * x[2], reverse=True)
            
            top_traits = [trait for trait, _, _ in trait_scores[:2] if trait_scores[0][1] > 0.6]
            
            if top_traits:
                trait_descriptions = {
                    "adventurous": "perfect for adventure seekers",
                    "cultural": "rich in cultural experiences",
                    "foodie": "a culinary delight",
                    "nature_lover": "immersed in natural beauty",
                    "history_buff": "steeped in fascinating history",
                    "social": "great for socializing and meeting people"
                }
                reasons = [trait_descriptions.get(trait, trait) for trait in top_traits]
        
        if reasons:
            return f"Recommended because it's {', '.join(reasons)}"
        elif score > 0.7:
            return "Highly recommended based on your interests"
        else:
            return "Matches your travel preferences"
    
    def _ensure_diversity(self, attractions: List[Dict], limit: int) -> List[Dict]:
        """Ensure recommendations have diversity in types"""
        if len(attractions) <= limit:
            return attractions
        
        selected = []
        type_counts = {}
        
        for att in attractions:
            att_type = att.get("type", "general")
            type_count = type_counts.get(att_type, 0)
            
            # Prefer diversity but still prioritize high scores
            if len(selected) < limit:
                if type_count < 2 or att.get("personality_match_score", 0) > 0.8:
                    selected.append(att)
                    type_counts[att_type] = type_count + 1
        
        # Fill remaining slots if needed
        for att in attractions:
            if len(selected) >= limit:
                break
            if att not in selected:
                selected.append(att)
        
        return selected[:limit]

    # ============================================================================
    # CHAIN PROMPT ENGINEERING METHODS
    # ============================================================================

    async def _map_traits_to_categories(
        self, user_profile: UserProfile
    ) -> Dict:
        """Step 1: Map personality traits to travel categories"""
        if not self.llm:
            # Fallback: simple mapping
            return {
                "primary_categories": ["general"],
                "secondary_categories": [],
                "travel_style": "balanced",
                "activity_intensity": "medium",
            }

        prompt_text = TRAIT_MAPPING_PROMPT.format(
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

        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a travel psychologist. Return ONLY valid JSON."),
                ("human", prompt_text),
            ])
            chain = prompt | self.llm
            response = await chain.ainvoke({})
            
            # Parse JSON response
            content = response.content if hasattr(response, "content") else str(response)
            return self._extract_json_safely(content)
        except Exception as e:
            print(f"Error in trait mapping: {e}")
            return {
                "primary_categories": ["general"],
                "secondary_categories": [],
                "travel_style": "balanced",
                "activity_intensity": "medium",
            }

    async def _inject_context(
        self, trait_mapping: Dict, scraped_data: Optional[Dict] = None
    ) -> Dict:
        """Step 2: Inject scraped data context"""
        if not self.llm:
            return {"matched_places": [], "recommendation_focus": "general"}

        # Format scraped data - escape curly braces for LangChain
        scraped_text = "No scraped data available"
        if scraped_data:
            scraped_json = json.dumps(scraped_data, indent=2)
            # Escape curly braces so LangChain doesn't interpret them as variables
            scraped_text = scraped_json.replace("{", "{{").replace("}", "}}")

        trait_mapping_json = json.dumps(trait_mapping, indent=2)
        # Escape curly braces so LangChain doesn't interpret them as variables
        trait_mapping_escaped = trait_mapping_json.replace("{", "{{").replace("}", "}}")

        prompt_text = CONTEXT_INJECTION_PROMPT.format(
            trait_mapping=trait_mapping_escaped,
            scraped_data=scraped_text,
        )

        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a data aggregator. Return ONLY valid JSON."),
                ("human", prompt_text),
            ])
            chain = prompt | self.llm
            response = await chain.ainvoke({})
            
            content = response.content if hasattr(response, "content") else str(response)
            return self._extract_json_safely(content)
        except Exception as e:
            print(f"Error in context injection: {e}")
            return {"matched_places": [], "recommendation_focus": "general"}

    async def get_recommendations_chained(
        self,
        user_profile: UserProfile,
        scraped_data: Optional[Dict] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Get recommendations using chain prompt engineering (3-step process)"""
        # Step 1: Map traits to categories
        trait_mapping = await self._map_traits_to_categories(user_profile)
        
        # Step 2: Inject context (scraped data)
        context = await self._inject_context(trait_mapping, scraped_data)
        
        # Step 3: Generate recommendations
        # Get attractions from vector search or use LLM-only filtering
        if self.vector_store:
            search_query = " ".join(trait_mapping.get("primary_categories", []))
            try:
                results = self.vector_store.similarity_search_with_score(
                    search_query, k=limit * 2
                )
                retrieved_attractions = []
                for doc, score in results:
                    attraction_id = doc.metadata.get("id")
                    attraction = next(
                        (att for att in self.attractions_data if str(att.get("id")) == str(attraction_id)),
                        None,
                    )
                    if attraction:
                        attraction["similarity_score"] = float(score)
                        retrieved_attractions.append(attraction)
            except Exception as e:
                # If vector search fails, fall back to LLM-only
                print(f"Vector search failed, using LLM-only: {e}")
                retrieved_attractions = self.attractions_data[:limit * 2]
        else:
            # No vector store available, use all attractions
            retrieved_attractions = self.attractions_data[:limit * 2]

        # Format attractions for prompt
        attractions_text = "\n\n".join(
            [
                f"{idx + 1}. {att['name']} ({att['type']})\n"
                f"   {att['description'][:200]}...\n"
                f"   Tags: {', '.join(att.get('tags', []))}"
                for idx, att in enumerate(retrieved_attractions[:20])
            ]
        )

        # Step 3: Generate recommendations
        if not self.llm:
            return self._rank_by_personality(retrieved_attractions, user_profile, limit)

        personality_traits = f"""
        - Adventurous: {user_profile.personality.adventurous}
        - Cultural: {user_profile.personality.cultural}
        - Foodie: {user_profile.personality.foodie}
        - Nature Lover: {user_profile.personality.nature_lover}
        - History Buff: {user_profile.personality.history_buff}
        - Social: {user_profile.personality.social}
        """

        # Escape JSON strings so LangChain doesn't interpret curly braces as variables
        trait_mapping_json = json.dumps(trait_mapping, indent=2)
        trait_mapping_escaped = trait_mapping_json.replace("{", "{{").replace("}", "}}")
        
        context_json = json.dumps(context, indent=2)
        context_escaped = context_json.replace("{", "{{").replace("}", "}}")

        prompt_text = RECOMMENDATION_GENERATION_PROMPT.format(
            personality_traits=personality_traits,
            travel_style=user_profile.preferences.travel_style or "not specified",
            budget_range=user_profile.preferences.budget_range or "not specified",
            trait_mapping=trait_mapping_escaped,
            context_data=context_escaped,
            available_places=attractions_text,
        )

        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a travel concierge AI. Provide personalized recommendations. For each recommendation, mention the attraction name clearly."),
                ("human", prompt_text),
            ])
            chain = prompt | self.llm
            response = await chain.ainvoke({})
            
            # Parse LLM response to extract recommended attractions
            content = response.content if hasattr(response, "content") else str(response)
            recommendations = self._parse_llm_recommendations(
                content, retrieved_attractions, user_profile, limit
            )
            
            if recommendations:
                return recommendations
            else:
                # Fallback to personality-based ranking if parsing fails
                return self._rank_by_personality(retrieved_attractions, user_profile, limit)
        except Exception as e:
            print(f"Error in chained recommendation: {e}")
            return self._rank_by_personality(retrieved_attractions, user_profile, limit)

    async def get_recommendations(
        self, 
        user_profile: UserProfile, 
        query: Optional[str] = None, 
        limit: int = 10,
        use_chained: bool = True,  # Use chain prompt engineering by default
    ) -> List[Dict]:
        """Get personalized recommendations based on user profile
        
        Args:
            user_profile: User profile with personality traits
            query: Optional search query
            limit: Maximum number of recommendations
            use_chained: If True, use 3-step chain prompt engineering
        """
        # Use chained approach if enabled and LLM available
        if use_chained and self.llm:
            try:
                # Try to get scraped data
                scraped_data = None
                try:
                    from app.scrapers.travel_scraper import travel_scraper
                    scraped_data = await travel_scraper.scrape_all()
                except Exception as e:
                    print(f"Note: Could not load scraped data: {e}")
                
                return await self.get_recommendations_chained(
                    user_profile, scraped_data=scraped_data, limit=limit
                )
            except Exception as e:
                print(f"Error in chained recommendations, falling back to standard: {e}")
                import traceback
                traceback.print_exc()
        
        # Fallback to standard approach
        if limit > settings.max_recommendation_limit:
            limit = settings.max_recommendation_limit

        # If vector store is not available, use LLM-only filtering
        if not self.vector_store:
            return await self._get_llm_only_recommendations(user_profile, query, limit)

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
            import traceback
            traceback.print_exc()
            return await self._get_llm_only_recommendations(user_profile, query, limit)

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

    async def _get_llm_only_recommendations(
        self, user_profile: UserProfile, query: Optional[str], limit: int
    ) -> List[Dict]:
        """Get recommendations using LLM-only filtering (no embeddings required).
        
        This method filters and ranks attractions using the LLM based on personality
        traits and preferences, without needing vector similarity search.
        """
        if not self.llm or not self.attractions_data:
            return self._get_mock_recommendations(user_profile, limit)
        
        # Prepare attraction data for LLM
        attractions_summary = []
        for att in self.attractions_data[:50]:  # Limit to first 50 for LLM processing
            summary = {
                "id": str(att.get("id", "")),
                "name": att.get("name", ""),
                "type": att.get("type", ""),
                "description": att.get("description", "")[:200],  # Truncate for token efficiency
                "tags": att.get("tags", [])[:5],
            }
            attractions_summary.append(summary)
        
        # Build prompt for LLM to filter and rank
        personality_str = json.dumps({
            "adventurous": user_profile.personality.adventurous,
            "cultural": user_profile.personality.cultural,
            "foodie": user_profile.personality.foodie,
            "nature_lover": user_profile.personality.nature_lover,
            "history_buff": user_profile.personality.history_buff,
            "social": user_profile.personality.social,
        }, indent=2)
        
        preferences_str = json.dumps({
            "budget_range": user_profile.preferences.budget_range or "not specified",
            "travel_style": user_profile.preferences.travel_style or "not specified",
            "interests": user_profile.preferences.interests,
        }, indent=2)
        
        attractions_json = json.dumps(attractions_summary, indent=2)
        
        prompt_text = f"""You are a travel recommendation expert for Bacolod, Philippines.

User Personality Traits:
{personality_str}

User Preferences:
{preferences_str}

Available Attractions ({len(attractions_summary)} total):
{attractions_json}

Task: Select and rank the top {limit} attractions that best match this user's personality and preferences.

Return ONLY a JSON array of attraction IDs in order of relevance (most relevant first).
Format: ["id1", "id2", "id3", ...]

Consider:
- Personality trait scores (higher = more important)
- Travel style and budget preferences
- User interests
- Attraction type and tags

Return ONLY the JSON array, no other text."""

        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a travel expert. Return ONLY a JSON array of attraction IDs."),
                ("human", prompt_text),
            ])
            chain = prompt | self.llm
            response = await chain.ainvoke({})
            
            content = response.content if hasattr(response, "content") else str(response)
            # Extract JSON array
            content = re.sub(r"```json\s*", "", content)
            content = re.sub(r"```\s*", "", content)
            content = content.strip()
            
            # Find array in response
            array_match = re.search(r'\[.*?\]', content, re.DOTALL)
            if array_match:
                selected_ids = json.loads(array_match.group(0))
            else:
                # Fallback: try parsing entire content
                selected_ids = json.loads(content)
            
            # Map IDs back to full attraction objects
            id_to_attraction = {str(att.get("id")): att for att in self.attractions_data}
            recommendations = []
            for att_id in selected_ids[:limit]:
                if att_id in id_to_attraction:
                    att = id_to_attraction[att_id].copy()
                    # Calculate personality match score
                    att["personality_match_score"] = self._calculate_match_score(
                        att, user_profile
                    )
                    recommendations.append(att)
            
            # If LLM didn't return enough, fill with personality-ranked attractions
            if len(recommendations) < limit:
                remaining = [
                    att for att in self.attractions_data
                    if str(att.get("id")) not in [r.get("id") for r in recommendations]
                ]
                ranked_remaining = self._rank_by_personality(
                    remaining, user_profile, limit - len(recommendations)
                )
                recommendations.extend(ranked_remaining)
            
            return recommendations[:limit]
            
        except Exception as e:
            print(f"Error in LLM-only recommendations: {e}")
            # Fallback to personality-based ranking
            return self._rank_by_personality(self.attractions_data, user_profile, limit)

    def _calculate_match_score(self, attraction: Dict, profile: UserProfile) -> float:
        """Calculate how well an attraction matches user personality."""
        score = 0.5  # Base score
        
        att_type = (attraction.get("type") or "").lower()
        att_tags = [tag.lower() for tag in attraction.get("tags", [])]
        att_desc = (attraction.get("description") or "").lower()
        
        # Food-related
        if profile.personality.foodie > 0.6:
            if "food" in att_type or "restaurant" in att_type or any("food" in t for t in att_tags):
                score += 0.3
        
        # History-related
        if profile.personality.history_buff > 0.6:
            if "historical" in att_type or "museum" in att_type or "heritage" in att_desc:
                score += 0.3
        
        # Nature-related
        if profile.personality.nature_lover > 0.6:
            if "nature" in att_type or "park" in att_type or "outdoor" in att_desc:
                score += 0.3
        
        # Culture-related
        if profile.personality.cultural > 0.6:
            if "cultural" in att_type or "festival" in att_type or "art" in att_desc:
                score += 0.3
        
        # Adventure-related
        if profile.personality.adventurous > 0.6:
            if "adventure" in att_type or "activity" in att_type:
                score += 0.3
        
        return min(score, 1.0)

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

    def _extract_json_safely(self, content: str) -> Dict:
        """Extract JSON from LLM response, handling multiple JSON objects and extra text.
        
        Handles cases where:
        - Response contains markdown code blocks (```json ... ```)
        - Multiple JSON objects in response
        - Extra text before/after JSON
        - Invalid JSON (returns empty dict)
        """
        if not content:
            return {}
        
        # Remove markdown code blocks if present
        content = re.sub(r"```json\s*", "", content)
        content = re.sub(r"```\s*", "", content)
        content = content.strip()
        
        # Try to find the first complete JSON object
        # Use a more precise approach: find balanced braces
        brace_count = 0
        start_idx = -1
        
        for i, char in enumerate(content):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    # Found a complete JSON object
                    json_str = content[start_idx:i+1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        # Try next JSON object
                        start_idx = -1
                        continue
        
        # Fallback: try parsing the entire content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Last resort: try to extract any JSON-like structure
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
        
        return {}

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
