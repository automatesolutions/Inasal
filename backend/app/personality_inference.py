"""LLM-based personality inference from social media profiles"""

import json
from typing import Dict, Optional
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import OutputFixingParser, PydanticOutputParser

from app.config import settings
from app.llm_factory import get_chat_llm
from app.user_profile import PersonalityTraits
from app.social_profile_parser import SocialProfileData

# Import prompt template
try:
    from app.prompts import PERSONALITY_INFERENCE_PROMPT
except ImportError:
    # Fallback if not available
    PERSONALITY_INFERENCE_PROMPT = """Analyze the following social media profile data and infer personality traits for a travel recommendation system."""


class PersonalityInferenceEngine:
    """Engine for inferring personality traits from social media data"""

    def __init__(self):
        # Use LLM factory (supports Ollama, OpenAI, Groq)
        self.llm = get_chat_llm(
            temperature=settings.personality_inference_temperature,
            model=None  # Use default model from llm_factory
        )

    async def infer_from_social_profile(self, social_data: SocialProfileData) -> PersonalityTraits:
        """Infer personality traits from social media profile data"""
        if not self.llm:
            # Return default traits if LLM not configured
            return PersonalityTraits()

        # Build prompt with social profile data
        prompt_text = PERSONALITY_INFERENCE_PROMPT.format(
            bio=social_data.bio or "Not provided",
            interests=", ".join(social_data.interests) if social_data.interests else "Not provided",
            posts="\n".join(social_data.posts_content[:5]) if social_data.posts_content else "Not provided",
            location=social_data.location or "Not provided",
            work_history=str(social_data.work_history) if social_data.work_history else "Not provided",
            education=str(social_data.education) if social_data.education else "Not provided",
        )

        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert psychologist specializing in personality analysis. Analyze the provided social media profile data and infer personality traits relevant to travel preferences. Return ONLY valid JSON with scores from 0.0 to 1.0 for each trait."),
            ("human", prompt_text),
        ])

        try:
            # Use Pydantic output parser to ensure correct format
            parser = PydanticOutputParser(pydantic_object=PersonalityTraits)
            fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=self.llm)

            chain = prompt | self.llm | fixing_parser
            result = await chain.ainvoke({})

            return result

        except Exception as e:
            print(f"Error in personality inference: {e}")
            # Fallback: infer from interests
            return await self._infer_from_interests(social_data.interests)

    async def infer_from_posts(self, posts: list[str]) -> PersonalityTraits:
        """Infer personality traits from post content"""
        if not self.llm or not posts:
            return PersonalityTraits()

        posts_text = "\n".join(posts[:10])  # Limit to 10 posts

        prompt_text = f"""Analyze the following social media posts and infer personality traits for travel preferences.

Posts:
{posts_text}

Return JSON with personality trait scores (0.0 to 1.0):
- adventurous: Interest in adventure and exploration
- cultural: Interest in arts, culture, traditions
- foodie: Interest in food and dining
- nature_lover: Interest in nature and outdoors
- history_buff: Interest in history and heritage
- social: Interest in social activities and events
"""

        try:
            parser = PydanticOutputParser(pydantic_object=PersonalityTraits)
            fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=self.llm)

            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a personality analysis expert. Return ONLY valid JSON."),
                ("human", prompt_text),
            ])

            chain = prompt | self.llm | fixing_parser
            result = await chain.ainvoke({})

            return result
        except Exception as e:
            print(f"Error inferring from posts: {e}")
            return PersonalityTraits()

    async def _infer_from_interests(self, interests: list[str]) -> PersonalityTraits:
        """Simple rule-based inference from interests (fallback)"""
        if not interests:
            return PersonalityTraits()

        interests_lower = [i.lower() for i in interests]

        # Rule-based mapping
        traits = PersonalityTraits()

        # Food-related
        food_keywords = ["food", "restaurant", "cooking", "cuisine", "dining", "eat"]
        if any(kw in " ".join(interests_lower) for kw in food_keywords):
            traits.foodie = 0.8

        # Adventure-related
        adventure_keywords = ["adventure", "travel", "explore", "outdoor", "sports"]
        if any(kw in " ".join(interests_lower) for kw in adventure_keywords):
            traits.adventurous = 0.8

        # Culture-related
        culture_keywords = ["art", "culture", "music", "festival", "tradition"]
        if any(kw in " ".join(interests_lower) for kw in culture_keywords):
            traits.cultural = 0.8

        # Nature-related
        nature_keywords = ["nature", "hiking", "beach", "mountain", "wildlife"]
        if any(kw in " ".join(interests_lower) for kw in nature_keywords):
            traits.nature_lover = 0.8

        # History-related
        history_keywords = ["history", "museum", "heritage", "ancient", "historical"]
        if any(kw in " ".join(interests_lower) for kw in history_keywords):
            traits.history_buff = 0.8

        # Social-related
        social_keywords = ["social", "event", "party", "friends", "community"]
        if any(kw in " ".join(interests_lower) for kw in social_keywords):
            traits.social = 0.8

        return traits

    async def infer_from_interests(self, interests: list[str]) -> PersonalityTraits:
        """Infer personality traits from interests list"""
        return await self._infer_from_interests(interests)


# Global instance
personality_inference_engine = PersonalityInferenceEngine()

