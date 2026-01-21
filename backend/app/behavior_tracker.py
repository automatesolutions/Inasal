"""Behavior tracking and adaptive personality updates"""

import asyncio
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import OutputFixingParser, PydanticOutputParser

from app.config import settings
from app.llm_factory import get_chat_llm
from app.user_profile import PersonalityTraits, UserProfileService
from app.bigquery_client import bigquery_client
from app.redis_client import redis_client

# Try to import OpenAI errors for quota handling
try:
    from openai import RateLimitError, APIError
except ImportError:
    # If OpenAI not installed, create dummy classes
    class RateLimitError(Exception):
        pass
    class APIError(Exception):
        pass

profile_service = UserProfileService()

# Track quota status globally
_quota_exceeded = False
_quota_exceeded_until = None
_last_analysis_attempt = {}  # Track last attempt per user to prevent spam


class BehaviorTracker:
    """Tracks user interactions and updates personality traits"""

    INTERACTION_TYPES = [
        "view_attraction",
        "click_detail",
        "save_attraction",
        "get_directions",
        "chat_message",
        "time_on_page",
        "return_visit",
        "share_attraction",
    ]

    def __init__(self):
        # Use LLM factory (supports Ollama, OpenAI, Groq)
        self.llm = get_chat_llm(
            temperature=0.3,
            model=None  # Use default model from llm_factory
        )

    async def log_interaction(
        self, user_id: str, interaction_type: str, data: Dict
    ) -> bool:
        """Log a user interaction"""
        try:
            interaction_log = {
                "user_id": user_id,
                "interaction_type": interaction_type,
                "content": data,
                "metadata": {},
                "timestamp": datetime.utcnow(),
            }

            await bigquery_client.insert_interaction_log(interaction_log)

            # Increment interaction counter in Redis
            counter_key = f"interactions:{user_id}:count"
            await redis_client.incr(counter_key)
            await redis_client.expire(counter_key, 86400)  # 24 hours

            # Check if we should trigger personality update
            count = await redis_client.get(counter_key)
            if count and int(count) >= settings.min_interactions_for_update:
                # Check if we should skip due to quota issues
                if not await self._should_skip_analysis(user_id):
                    # Trigger personality update (async, don't wait)
                    asyncio.create_task(self.analyze_and_update_personality(user_id))
                else:
                    print(f"⚠️  Skipping personality analysis for {user_id} due to quota/rate limits")

            return True

        except Exception as e:
            print(f"Error logging interaction: {e}")
            return False

    async def get_recent_interactions(
        self, user_id: str, limit: int = 50
    ) -> List[Dict]:
        """Get recent interactions for a user"""
        try:
            return await bigquery_client.get_interaction_history(user_id, limit)
        except Exception as e:
            print(f"Error getting interactions: {e}")
            return []

    async def _reset_quota_flags_if_needed(self):
        """Automatically clear quota flags for providers without rate limits (e.g., Ollama)"""
        global _quota_exceeded, _quota_exceeded_until
        if settings.llm_provider.lower() != "openai":
            _quota_exceeded = False
            _quota_exceeded_until = None

    async def _should_skip_analysis(self, user_id: str) -> bool:
        """Check if we should skip analysis due to quota/rate limits"""
        global _quota_exceeded, _quota_exceeded_until

        # Providers like Ollama/Groq don't enforce OpenAI-style quotas
        if settings.llm_provider.lower() != "openai":
            await self._reset_quota_flags_if_needed()
            return False
        
        # Check global quota status
        if _quota_exceeded and _quota_exceeded_until:
            if datetime.utcnow() < _quota_exceeded_until:
                return True
            else:
                # Reset quota status after cooldown
                _quota_exceeded = False
                _quota_exceeded_until = None
        
        # Check rate limiting per user (prevent spam)
        user_key = f"analysis_attempt:{user_id}"
        last_attempt = await redis_client.get(user_key)
        if last_attempt:
            last_time = float(last_attempt)
            # Only allow one analysis per user per 5 minutes
            if time.time() - last_time < 300:  # 5 minutes
                return True
        
        return False

    async def _mark_analysis_attempt(self, user_id: str):
        """Mark that we attempted analysis for this user"""
        user_key = f"analysis_attempt:{user_id}"
        await redis_client.set(user_key, str(time.time()), expire=300)  # 5 minute TTL

    async def analyze_behavior_patterns(self, user_id: str) -> PersonalityTraits:
        """Analyze behavior patterns and infer updated personality traits"""
        global _quota_exceeded, _quota_exceeded_until
        
        if not self.llm:
            # Return current personality if LLM not available
            profile = await profile_service.get_profile(user_id)
            return profile.personality if profile else PersonalityTraits()

        # Mark that we're attempting analysis
        await self._mark_analysis_attempt(user_id)

        # Get recent interactions
        interactions = await self.get_recent_interactions(user_id, limit=50)

        if not interactions:
            return PersonalityTraits()

        # Format interactions for analysis
        interaction_summary = []
        for interaction in interactions[:30]:  # Limit to 30 most recent
            interaction_type = interaction.get("interaction_type", "")
            data = interaction.get("data", {})
            
            summary = f"- {interaction_type}: {data.get('attraction_name', data.get('message', 'N/A'))}"
            interaction_summary.append(summary)

        interactions_text = "\n".join(interaction_summary)

        # Get current personality
        profile = await profile_service.get_profile(user_id)
        current_personality = profile.personality if profile else PersonalityTraits()

        # Create prompt for LLM
        prompt_text = f"""Analyze user behavior patterns and update personality trait scores.

Recent Interactions (last 30):
{interactions_text}

Current Personality Traits:
- adventurous: {current_personality.adventurous}
- cultural: {current_personality.cultural}
- foodie: {current_personality.foodie}
- nature_lover: {current_personality.nature_lover}
- history_buff: {current_personality.history_buff}
- social: {current_personality.social}

Based on the user's recent behavior (which attractions they viewed, saved, spent time on, etc.),
infer updated personality trait scores (0.0 to 1.0). Consider:
- Types of attractions they interact with most
- Patterns in their browsing behavior
- Consistency of interests

Return JSON with updated personality trait scores.
"""

        # Declare global variables at the start of the try block
        global _quota_exceeded, _quota_exceeded_until
        
        try:
            parser = PydanticOutputParser(pydantic_object=PersonalityTraits)
            fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=self.llm)

            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a behavior analyst. Analyze user interactions and update personality traits. Return ONLY valid JSON."),
                ("human", prompt_text),
            ])

            chain = prompt | self.llm | fixing_parser
            updated_traits = await chain.ainvoke({})

            # Reset quota status on success
            if _quota_exceeded:
                _quota_exceeded = False
                _quota_exceeded_until = None

            return updated_traits

        except RateLimitError as e:
            # Handle rate limit errors
            if settings.llm_provider.lower() == "openai":
                _quota_exceeded = True
                # Set cooldown period: 1 hour from now
                _quota_exceeded_until = datetime.utcnow() + timedelta(hours=1)
                print(f"⚠️  OpenAI rate limit exceeded. Pausing behavior analysis for 1 hour.")
                print(f"   Error: {e}")
            else:
                await self._reset_quota_flags_if_needed()
            return current_personality
        
        except APIError as e:
            # Handle API errors (including quota errors and memory errors)
            error_str = str(e)
            if "quota" in error_str.lower() or "429" in error_str:
                if settings.llm_provider.lower() == "openai":
                    _quota_exceeded = True
                    # Set cooldown period: 1 hour from now
                    _quota_exceeded_until = datetime.utcnow() + timedelta(hours=1)
                    print(f"⚠️  OpenAI quota exceeded. Pausing behavior analysis for 1 hour.")
                    print(f"   Error: {e}")
                else:
                    await self._reset_quota_flags_if_needed()
                return current_personality
            elif "memory" in error_str.lower() or "requires more system memory" in error_str.lower():
                print(f"⚠️  Model memory error: {e}")
                print(f"   Tip: Use a smaller model (e.g., llama3.2:1b) or free up system memory")
                print(f"   Command: ollama pull llama3.2:1b")
                print(f"   Then set OLLAMA_MODEL=llama3.2:1b in .env")
                return current_personality
            else:
                print(f"⚠️  OpenAI API error: {e}")
                return current_personality

        except Exception as e:
            error_str = str(e)
            # Check if it's a quota error in the error message
            if "quota" in error_str.lower() or "429" in error_str or "insufficient_quota" in error_str:
                if settings.llm_provider.lower() == "openai":
                    _quota_exceeded = True
                    _quota_exceeded_until = datetime.utcnow() + timedelta(hours=1)
                    print(f"⚠️  OpenAI quota exceeded (detected in error message). Pausing behavior analysis for 1 hour.")
                else:
                    await self._reset_quota_flags_if_needed()
            else:
                print(f"Error analyzing behavior patterns: {e}")
            return current_personality

    async def analyze_and_update_personality(self, user_id: str) -> bool:
        """Analyze behavior and update personality traits in database"""
        try:
            # Get current personality to compare
            profile = await profile_service.get_profile(user_id)
            if not profile:
                return False
            
            current_traits = profile.personality
            
            # Get updated personality from behavior analysis
            updated_traits = await self.analyze_behavior_patterns(user_id)

            # Check if traits actually changed (avoid unnecessary updates)
            if updated_traits.model_dump() == current_traits.model_dump():
                # No change, skip update
                return True

            # Update profile with new traits
            await profile_service.update_personality(user_id, updated_traits)

            # Reset interaction counter
            counter_key = f"interactions:{user_id}:count"
            await redis_client.delete(counter_key)

            # Store update history
            if hasattr(profile, 'personality_update_history'):
                update_history = profile.personality_update_history or []
                update_history.append({
                    "updated_at": datetime.utcnow().isoformat(),
                    "personality": updated_traits.model_dump(),
                })
                # Note: This would require updating the UserProfile model to include update_history
                # For now, we'll just update the personality

            print(f"✅ Updated personality for user {user_id} based on behavior")
            return True

        except Exception as e:
            print(f"Error updating personality from behavior: {e}")
            return False

    async def should_update_personality(self, user_id: str) -> bool:
        """Check if personality should be updated based on time and interactions"""
        try:
            profile = await profile_service.get_profile(user_id)
            if not profile:
                return False

            # Check last update time (if stored)
            # For now, check interaction count
            counter_key = f"interactions:{user_id}:count"
            count = await redis_client.get(counter_key)
            
            if count and int(count) >= settings.min_interactions_for_update:
                return True

            return False

        except Exception as e:
            print(f"Error checking update eligibility: {e}")
            return False


# Global instance
behavior_tracker = BehaviorTracker()

