"""Personality analysis from social media data"""

import json
import logging
from typing import Dict, Any
from app.llm_factory import get_chat_llm
from app.user_profile import PersonalityTraits

logger = logging.getLogger(__name__)


class PersonalityAnalyzer:
    """Analyze personality from social media data"""

    def __init__(self):
        self.llm = get_chat_llm(temperature=0.3)  # Lower temp for analysis

    async def summarize_social_data(
        self,
        scraped_data: Dict[str, Any]
    ) -> str:
        """
        Summarize scraped social media data using LLM
        """
        summary_prompt = f"""
        Summarize the following social media profile data into a concise 
        personality profile. Focus on interests, activities, preferences, 
        and behavioral patterns.
        
        Profile Data:
        - Bio: {scraped_data.get('bio', 'N/A')}
        - Recent Posts: {scraped_data.get('posts_content', [])[:10]}
        - Interests: {scraped_data.get('interests', [])}
        - Location: {scraped_data.get('location', 'N/A')}
        
        Provide a comprehensive summary that captures:
        1. Main interests and hobbies
        2. Travel preferences (if mentioned)
        3. Social behavior patterns
        4. Activity preferences (outdoor, cultural, food, etc.)
        5. Personality indicators
        
        Summary:
        """
        
        try:
            response = await self.llm.ainvoke(summary_prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"Error summarizing social data: {e}")
            return "Unable to analyze social media profile data."

    async def analyze_personality_from_summary(
        self,
        summary: str
    ) -> PersonalityTraits:
        """
        Analyze personality traits from summarized social data
        """
        analysis_prompt = f"""
        Analyze the following personality summary and assign scores 
        (0.0 to 1.0) for each travel-related personality trait.
        
        Personality Summary:
        {summary}
        
        Traits to analyze:
        - adventurous: Enjoys outdoor activities, adventure sports, exploring new places
        - cultural: Interested in arts, festivals, local traditions, museums
        - foodie: Loves trying new foods, restaurants, culinary experiences
        - nature_lover: Enjoys beaches, mountains, parks, natural scenery
        - history_buff: Interested in historical sites, architecture, heritage
        - social: Enjoys social gatherings, events, meeting people, nightlife
        
        Return ONLY valid JSON in this exact format:
        {{
            "adventurous": 0.0-1.0,
            "cultural": 0.0-1.0,
            "foodie": 0.0-1.0,
            "nature_lover": 0.0-1.0,
            "history_buff": 0.0-1.0,
            "social": 0.0-1.0,
            "reasoning": "Brief explanation of scores"
        }}
        """
        
        try:
            response = await self.llm.ainvoke(analysis_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            # Try to extract JSON from response (handle markdown code blocks)
            content = content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            personality_json = json.loads(content)
            
            return PersonalityTraits(
                adventurous=float(personality_json.get("adventurous", 0.5)),
                cultural=float(personality_json.get("cultural", 0.5)),
                foodie=float(personality_json.get("foodie", 0.5)),
                nature_lover=float(personality_json.get("nature_lover", 0.5)),
                history_buff=float(personality_json.get("history_buff", 0.5)),
                social=float(personality_json.get("social", 0.5))
            )
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing personality JSON: {e}")
            # Fallback to default personality
            return PersonalityTraits()
        except Exception as e:
            logger.error(f"Error analyzing personality: {e}")
            return PersonalityTraits()
