"""LangGraph workflow: Social Media Search → Personality → Recommendations"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from pydantic import BaseModel, Field

from app.mcp_brightdata_client import mcp_brightdata_client
from app.llm_factory import get_chat_llm
from app.prompts import (
    SOCIAL_MEDIA_SUMMARY_PROMPT,
    PERSONALITY_INFERENCE_WITH_HIDDEN_PROMPT,
    RECOMMENDATION_GENERATION_PROMPT,
    SECRET_RECOMMENDATION_PROMPT,
)
from app.redis_client import redis_client
from app.user_profile import UserProfileService

logger = logging.getLogger(__name__)

profile_service = UserProfileService()


# Pydantic models for structured output
class SocialSummary(BaseModel):
    bio: str = Field(default="", description="Bio/About section")
    interests: List[str] = Field(default_factory=list, description="List of interests")
    location: str = Field(default="", description="Location")
    work_history: List[str] = Field(default_factory=list, description="Work history")
    education: List[str] = Field(default_factory=list, description="Education")
    social_patterns: str = Field(default="", description="Social activity patterns")
    communication_style: str = Field(default="", description="Communication style")


class PersonalityTraitsResponse(BaseModel):
    visible_traits: Dict[str, float] = Field(description="Visible personality traits")
    hidden_traits: Dict[str, float] = Field(description="Hidden personality traits")
    reasoning: str = Field(default="", description="Reasoning for traits")


class RecommendationsResponse(BaseModel):
    hotels: List[Dict[str, Any]] = Field(default_factory=list)
    restaurants: List[Dict[str, Any]] = Field(default_factory=list)
    entertainment: List[Dict[str, Any]] = Field(default_factory=list)
    tourist_spots: List[Dict[str, Any]] = Field(default_factory=list)


class SecretRecommendationsResponse(BaseModel):
    secret_recommendations: List[Dict[str, Any]] = Field(default_factory=list)


def _keep_existing(old: Optional[Any], new: Optional[Any]) -> Optional[Any]:
    return old if old is not None else new


def _set_latest(_old: Optional[Any], new: Optional[Any]) -> Optional[Any]:
    return new


def _extend_list(old: Optional[List[Any]], new: Optional[List[Any]]) -> List[Any]:
    combined = list(old or [])
    combined.extend(new or [])
    return combined


def _merge_dicts(old: Optional[Dict[str, Any]], new: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(old or {})
    for key, value in (new or {}).items():
        merged[key] = value
    return merged


class PersonaDiscoveryState(TypedDict, total=False):
    """State container for the persona discovery LangGraph pipeline."""

    user_id: Annotated[str, _keep_existing]
    first_name: Annotated[str, _keep_existing]
    last_name: Annotated[str, _keep_existing]
    full_name: Annotated[str, _keep_existing]
    
    # Social media search results
    linkedin_data: Annotated[Dict[str, Any], _merge_dicts]
    twitter_data: Annotated[Dict[str, Any], _merge_dicts]
    facebook_data: Annotated[Dict[str, Any], _merge_dicts]
    
    # Summarized data
    social_summary: Annotated[Dict[str, Any], _merge_dicts]
    
    # Personality traits
    personality_traits: Annotated[Dict[str, float], _merge_dicts]
    hidden_traits: Annotated[Dict[str, float], _merge_dicts]
    
    # Recommendations
    hotels: Annotated[List[Dict[str, Any]], _extend_list]
    restaurants: Annotated[List[Dict[str, Any]], _extend_list]
    entertainment: Annotated[List[Dict[str, Any]], _extend_list]
    tourist_spots: Annotated[List[Dict[str, Any]], _extend_list]
    secret_recommendations: Annotated[List[Dict[str, Any]], _extend_list]
    
    errors: Annotated[List[str], _extend_list]
    log: Annotated[List[str], _extend_list]


class PersonaDiscoveryWorkflow:
    """Configures and executes the social media-based persona discovery workflow."""

    def __init__(self) -> None:
        self._llm = get_chat_llm(temperature=0.3)
        self.graph = self._build_graph()

    async def run(
        self,
        user_id: str,
        first_name: str,
        last_name: str,
    ) -> Dict[str, Any]:
        """Execute the persona discovery workflow."""
        full_name = f"{first_name} {last_name}".strip()
        
        initial_state: PersonaDiscoveryState = {
            "user_id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "linkedin_data": {},
            "twitter_data": {},
            "facebook_data": {},
            "social_summary": {},
            "personality_traits": {},
            "hidden_traits": {},
            "hotels": [],
            "restaurants": [],
            "entertainment": [],
            "tourist_spots": [],
            "secret_recommendations": [],
            "errors": [],
            "log": [],
        }

        try:
            result = await self.graph.ainvoke(initial_state)
            return result
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            initial_state["errors"].append(f"Workflow failed: {str(e)}")
            return initial_state

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        graph = StateGraph(PersonaDiscoveryState)

        # Add nodes
        graph.add_node("search_linkedin", self._search_linkedin)
        graph.add_node("search_twitter", self._search_twitter)
        graph.add_node("search_facebook", self._search_facebook)
        graph.add_node("summarize_social_data", self._summarize_social_data)
        graph.add_node("infer_personality", self._infer_personality)
        graph.add_node("generate_recommendations", self._generate_recommendations)
        graph.add_node("generate_secret_recommendations", self._generate_secret_recommendations)
        graph.add_node("save_results", self._save_results)

        # Set entry point
        graph.set_entry_point("search_linkedin")

        # Parallel social media searches
        graph.add_edge("search_linkedin", "search_twitter")
        graph.add_edge("search_twitter", "search_facebook")
        graph.add_edge("search_facebook", "summarize_social_data")

        # Sequential processing
        graph.add_edge("summarize_social_data", "infer_personality")
        graph.add_edge("infer_personality", "generate_recommendations")
        graph.add_edge("generate_recommendations", "generate_secret_recommendations")
        graph.add_edge("generate_secret_recommendations", "save_results")
        graph.add_edge("save_results", END)

        return graph.compile()

    async def _search_linkedin(self, state: PersonaDiscoveryState) -> Dict[str, Any]:
        """Search LinkedIn for the person."""
        try:
            full_name = state.get("full_name", "")
            first_name = state.get("first_name", "")
            last_name = state.get("last_name", "")
            
            # Use full_name if available, otherwise construct from first_name and last_name
            if not full_name:
                full_name = f"{first_name} {last_name}".strip()
            
            # Ensure we have at least a first name for LinkedIn search
            if not first_name:
                logger.warning(f"No first_name provided for LinkedIn search. State: first_name='{first_name}', last_name='{last_name}', full_name='{full_name}'")
                return {"linkedin_data": {}}
            
            logger.info(f"Searching LinkedIn for: {first_name} {last_name} (full: {full_name})")
            
            result = await mcp_brightdata_client.search_linkedin(
                full_name, 
                first_name=first_name,
                last_name=last_name,
                limit=10
            )
            
            if result.get("success"):
                data = result.get("data", {})
                state["log"].append(f"LinkedIn search completed")
                logger.info(f"LinkedIn search successful")
                return {"linkedin_data": data}
            else:
                error_msg = result.get("error", "Unknown error")
                logger.warning(f"LinkedIn search failed: {error_msg}, continuing with empty data")
                state["errors"].append(f"LinkedIn search failed: {error_msg}")
                return {"linkedin_data": {}}
        except Exception as e:
            logger.error(f"LinkedIn search error: {e}", exc_info=True)
            state["errors"].append(f"LinkedIn search error: {str(e)}")
            return {"linkedin_data": {}}

    async def _search_twitter(self, state: PersonaDiscoveryState) -> Dict[str, Any]:
        """Search Twitter/X for the person."""
        try:
            full_name = state.get("full_name", "")
            first_name = state.get("first_name", "")
            last_name = state.get("last_name", "")
            
            if not full_name:
                full_name = f"{first_name} {last_name}".strip()
            
            if not full_name:
                logger.warning(f"No name provided for Twitter search. State: first_name='{first_name}', last_name='{last_name}', full_name='{full_name}'")
                return {"twitter_data": {}}
            
            logger.info(f"Searching Twitter for: {full_name}")
            
            result = await mcp_brightdata_client.search_twitter(full_name, limit=10)
            
            if result.get("success"):
                data = result.get("data", {})
                state["log"].append(f"Twitter search completed")
                logger.info(f"Twitter search successful")
                return {"twitter_data": data}
            else:
                error_msg = result.get("error", "Unknown error")
                logger.warning(f"Twitter search failed: {error_msg}, continuing with empty data")
                state["errors"].append(f"Twitter search failed: {error_msg}")
                return {"twitter_data": {}}
        except Exception as e:
            logger.error(f"Twitter search error: {e}", exc_info=True)
            state["errors"].append(f"Twitter search error: {str(e)}")
            return {"twitter_data": {}}

    async def _search_facebook(self, state: PersonaDiscoveryState) -> Dict[str, Any]:
        """Search Facebook for the person."""
        try:
            full_name = state.get("full_name", "")
            first_name = state.get("first_name", "")
            last_name = state.get("last_name", "")
            
            if not full_name:
                full_name = f"{first_name} {last_name}".strip()
            
            if not full_name:
                logger.warning(f"No name provided for Facebook search. State: first_name='{first_name}', last_name='{last_name}', full_name='{full_name}'")
                return {"facebook_data": {}}
            
            logger.info(f"Searching Facebook for: {full_name}")
            
            result = await mcp_brightdata_client.search_facebook(full_name, limit=10)
            
            if result.get("success"):
                data = result.get("data", {})
                state["log"].append(f"Facebook search completed")
                logger.info(f"Facebook search successful")
                return {"facebook_data": data}
            else:
                error_msg = result.get("error", "Unknown error")
                logger.warning(f"Facebook search failed: {error_msg}, continuing with empty data")
                state["errors"].append(f"Facebook search failed: {error_msg}")
                return {"facebook_data": {}}
        except Exception as e:
            logger.error(f"Facebook search error: {e}", exc_info=True)
            state["errors"].append(f"Facebook search error: {str(e)}")
            return {"facebook_data": {}}

    async def _summarize_social_data(self, state: PersonaDiscoveryState) -> Dict[str, Any]:
        """Summarize social media data using LLM with structured output."""
        try:
            full_name = state.get("full_name", "")
            linkedin_data = state.get("linkedin_data", {})
            twitter_data = state.get("twitter_data", {})
            facebook_data = state.get("facebook_data", {})
            
            # Check if we have any data
            has_data = bool(linkedin_data or twitter_data or facebook_data)
            
            if not has_data:
                # No social media data - create default summary based on name
                logger.info(f"No social media data found for {full_name}, using name-based inference")
                summary = SocialSummary(
                    bio=f"{full_name} is planning a trip to Bacolod, Philippines.",
                    interests=["travel", "exploration"],
                    location="Unknown",
                    work_history=[],
                    education=[],
                    social_patterns="Unknown",
                    communication_style="Unknown"
                )
                return {"social_summary": summary.model_dump()}

            # Use Pydantic parser to force JSON output
            parser = PydanticOutputParser(pydantic_object=SocialSummary)
            fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=self._llm)
            
            prompt_text = SOCIAL_MEDIA_SUMMARY_PROMPT.format(
                full_name=full_name,
                linkedin_data=json.dumps(linkedin_data, indent=2),
                twitter_data=json.dumps(twitter_data, indent=2),
                facebook_data=json.dumps(facebook_data, indent=2),
            )

            messages = [
                SystemMessage(content="You are an expert at analyzing social media profiles. You MUST return valid JSON only, no additional text."),
                HumanMessage(content=f"{prompt_text}\n\n{parser.get_format_instructions()}"),
            ]

            try:
                response = await self._llm.ainvoke(messages)
                # Parse with fixing parser
                summary = await fixing_parser.aparse(response.content)
                summary_dict = summary.model_dump() if isinstance(summary, SocialSummary) else summary
            except Exception as llm_error:
                error_str = str(llm_error)
                logger.error(f"LLM invocation failed: {error_str}")
                if "404" in error_str or "not_found" in error_str.lower():
                    logger.error(f"Model not found. Current model: {self._llm.model_name if hasattr(self._llm, 'model_name') else 'unknown'}")
                # Fallback to default
                summary_dict = SocialSummary(bio=f"{full_name} is planning a trip to Bacolod.").model_dump()
            
            state["log"].append("Social media data summarized")
            return {"social_summary": summary_dict}
        except Exception as e:
            logger.error(f"Social data summarization error: {e}")
            state["errors"].append(f"Social data summarization error: {str(e)}")
            # Return default summary
            full_name = state.get("full_name", "User")
            return {"social_summary": SocialSummary(bio=f"{full_name} is planning a trip to Bacolod.").model_dump()}

    async def _infer_personality(self, state: PersonaDiscoveryState) -> Dict[str, Any]:
        """Infer personality traits from social summary with structured output."""
        try:
            social_summary = state.get("social_summary", {})
            
            # Use Pydantic parser to force JSON output
            parser = PydanticOutputParser(pydantic_object=PersonalityTraitsResponse)
            fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=self._llm)

            prompt_text = PERSONALITY_INFERENCE_WITH_HIDDEN_PROMPT.format(
                social_summary=json.dumps(social_summary, indent=2),
            )

            messages = [
                SystemMessage(content="You are a personality psychologist. You MUST return valid JSON only, no additional text."),
                HumanMessage(content=f"{prompt_text}\n\n{parser.get_format_instructions()}"),
            ]

            try:
                response = await self._llm.ainvoke(messages)
                personality_data = await fixing_parser.aparse(response.content)
                
                if isinstance(personality_data, PersonalityTraitsResponse):
                    visible_traits = personality_data.visible_traits
                    hidden_traits = personality_data.hidden_traits
                else:
                    visible_traits = personality_data.get("visible_traits", {})
                    hidden_traits = personality_data.get("hidden_traits", {})
            except Exception as e:
                logger.error(f"Personality parsing error: {e}")
                # Fallback to default traits
                visible_traits = {
                    "adventurous": 0.5,
                    "cultural": 0.5,
                    "foodie": 0.5,
                    "nature_lover": 0.5,
                    "history_buff": 0.5,
                    "social": 0.5,
                }
                hidden_traits = {
                    "introverted_extroverted": 0.5,
                    "risk_taker": 0.5,
                    "luxury_seeker": 0.3,
                    "budget_conscious": 0.7,
                    "nightlife_lover": 0.5,
                    "offbeat_explorer": 0.5,
                    "local_culture_seeker": 0.5,
                }
            
            state["log"].append("Personality traits inferred")
            
            # Save to database
            from app.user_profile import PersonalityTraits
            personality_obj = PersonalityTraits(**visible_traits)
            await profile_service.update_personality(state["user_id"], personality_obj)
            
            return {
                "personality_traits": visible_traits,
                "hidden_traits": hidden_traits,
            }
        except Exception as e:
            logger.error(f"Personality inference error: {e}")
            state["errors"].append(f"Personality inference error: {str(e)}")
            # Return default traits
            return {
                "personality_traits": {
                    "adventurous": 0.5,
                    "cultural": 0.5,
                    "foodie": 0.5,
                    "nature_lover": 0.5,
                    "history_buff": 0.5,
                    "social": 0.5,
                },
                "hidden_traits": {
                    "introverted_extroverted": 0.5,
                    "risk_taker": 0.5,
                    "luxury_seeker": 0.3,
                    "budget_conscious": 0.7,
                    "nightlife_lover": 0.5,
                    "offbeat_explorer": 0.5,
                    "local_culture_seeker": 0.5,
                },
            }

    async def _generate_recommendations(self, state: PersonaDiscoveryState) -> Dict[str, Any]:
        """Generate recommendations based on personality with structured output."""
        try:
            personality_traits = state.get("personality_traits", {})
            hidden_traits = state.get("hidden_traits", {})
            
            if not personality_traits:
                logger.warning("No personality traits available, using defaults")
                personality_traits = {
                    "adventurous": 0.5,
                    "cultural": 0.5,
                    "foodie": 0.5,
                    "nature_lover": 0.5,
                    "history_buff": 0.5,
                    "social": 0.5,
                }

            # Use Pydantic parser
            parser = PydanticOutputParser(pydantic_object=RecommendationsResponse)
            fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=self._llm)

            prompt_text = RECOMMENDATION_GENERATION_PROMPT.format(
                personality_traits=json.dumps(personality_traits, indent=2),
                hidden_traits=json.dumps(hidden_traits, indent=2),
            )

            messages = [
                SystemMessage(content="You are an expert travel guide for Bacolod, Philippines. You MUST return valid JSON only."),
                HumanMessage(content=f"{prompt_text}\n\n{parser.get_format_instructions()}"),
            ]

            try:
                response = await self._llm.ainvoke(messages)
                recommendations = await fixing_parser.aparse(response.content)
                
                logger.info(f"LLM response received, parsing recommendations...")
                
                if isinstance(recommendations, RecommendationsResponse):
                    result = {
                        "hotels": recommendations.hotels or [],
                        "restaurants": recommendations.restaurants or [],
                        "entertainment": recommendations.entertainment or [],
                        "tourist_spots": recommendations.tourist_spots or [],
                    }
                else:
                    result = {
                        "hotels": recommendations.get("hotels", []) or [],
                        "restaurants": recommendations.get("restaurants", []) or [],
                        "entertainment": recommendations.get("entertainment", []) or [],
                        "tourist_spots": recommendations.get("tourist_spots", []) or [],
                    }
                
                logger.info(f"Generated {len(result['hotels'])} hotels, {len(result['restaurants'])} restaurants, {len(result['entertainment'])} entertainment, {len(result['tourist_spots'])} tourist spots")
            except Exception as e:
                logger.error(f"Recommendation parsing error: {e}", exc_info=True)
                # Don't use fallback - return empty recommendations if LLM fails
                result = {
                    "hotels": [],
                    "restaurants": [],
                    "entertainment": [],
                    "tourist_spots": [],
                }
                logger.error("Failed to generate recommendations - MCP Bright Data data required")
            
            state["log"].append("Recommendations generated")
            return result
        except Exception as e:
            logger.error(f"Recommendation generation error: {e}", exc_info=True)
            state["errors"].append(f"Recommendation generation error: {str(e)}")
            # Don't use fallback - return empty recommendations if generation fails
            logger.error("Failed to generate recommendations - MCP Bright Data data required")
            return {
                "hotels": [],
                "restaurants": [],
                "entertainment": [],
                "tourist_spots": [],
            }

    async def _generate_secret_recommendations(self, state: PersonaDiscoveryState) -> Dict[str, Any]:
        """Generate secret recommendations based on hidden traits with structured output."""
        try:
            hidden_traits = state.get("hidden_traits", {})
            
            if not hidden_traits:
                return {"secret_recommendations": []}

            # Use Pydantic parser
            parser = PydanticOutputParser(pydantic_object=SecretRecommendationsResponse)
            fixing_parser = OutputFixingParser.from_llm(parser=parser, llm=self._llm)

            prompt_text = SECRET_RECOMMENDATION_PROMPT.format(
                hidden_traits=json.dumps(hidden_traits, indent=2),
            )

            messages = [
                SystemMessage(content="You are a travel curator. You MUST return valid JSON only."),
                HumanMessage(content=f"{prompt_text}\n\n{parser.get_format_instructions()}"),
            ]

            try:
                response = await self._llm.ainvoke(messages)
                secret_data = await fixing_parser.aparse(response.content)
                
                if isinstance(secret_data, SecretRecommendationsResponse):
                    secret_recommendations = secret_data.secret_recommendations
                else:
                    secret_recommendations = secret_data.get("secret_recommendations", [])
            except Exception as e:
                logger.error(f"Secret recommendation parsing error: {e}")
                secret_recommendations = []
            
            state["log"].append("Secret recommendations generated")
            
            return {
                "secret_recommendations": secret_recommendations,
            }
        except Exception as e:
            logger.error(f"Secret recommendation generation error: {e}")
            state["errors"].append(f"Secret recommendation generation error: {str(e)}")
            return {"secret_recommendations": []}

    async def _save_results(self, state: PersonaDiscoveryState) -> Dict[str, Any]:
        """Save results to Redis cache."""
        try:
            user_id = state.get("user_id")
            
            hotels = state.get("hotels", [])
            restaurants = state.get("restaurants", [])
            entertainment = state.get("entertainment", [])
            tourist_spots = state.get("tourist_spots", [])
            secret_recommendations = state.get("secret_recommendations", [])
            
            logger.info(f"Saving recommendations for user {user_id}:")
            logger.info(f"  Hotels: {len(hotels)}")
            logger.info(f"  Restaurants: {len(restaurants)}")
            logger.info(f"  Entertainment: {len(entertainment)}")
            logger.info(f"  Tourist Spots: {len(tourist_spots)}")
            logger.info(f"  Secret: {len(secret_recommendations)}")
            
            recommendations_data = {
                "hotels": hotels,
                "restaurants": restaurants,
                "entertainment": entertainment,
                "tourist_spots": tourist_spots,
                "secret_recommendations": secret_recommendations,
            }
            
            await redis_client.set(
                f"recommendations:{user_id}",
                json.dumps(recommendations_data),
                expire=3600 * 24,  # 24 hours
            )
            
            state["log"].append("Results saved to cache")
            logger.info(f"✅ Recommendations saved to Redis for user {user_id}")
            return {}
        except Exception as e:
            logger.error(f"Save results error: {e}", exc_info=True)
            state["errors"].append(f"Save results error: {str(e)}")
            return {}

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response, handling markdown and extra text."""
        import re
        
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        
        # Try to find JSON object directly
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from: {text[:200]}")
            return {}


# Global instance
persona_discovery_graph = PersonaDiscoveryWorkflow()

