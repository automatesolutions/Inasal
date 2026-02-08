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
        # Check if data is actually empty
        has_data = (
            scraped_data.get('bio') and scraped_data.get('bio') != 'N/A' and scraped_data.get('bio').strip()
        ) or (
            scraped_data.get('posts_content') and len(scraped_data.get('posts_content', [])) > 0
        ) or (
            scraped_data.get('interests') and len(scraped_data.get('interests', [])) > 0
        )
        
        if not has_data:
            # Return a message indicating we should use SERP instead
            return "Social media profile data is empty or unavailable. Use SERP Google search results instead."
        
        summary_prompt = f"""
        Summarize the following social media profile data into a concise 
        personality profile. Focus on interests, activities, preferences, 
        and behavioral patterns.
        
        IMPORTANT: If the data is sparse, make reasonable inferences. Do NOT say 
        "lack of information" - instead, extract what you can and infer personality 
        traits from available context.
        
        Profile Data:
        - Bio: {scraped_data.get('bio', 'N/A')}
        - Recent Posts: {scraped_data.get('posts_content', [])[:10]}
        - Interests: {scraped_data.get('interests', [])}
        - Location: {scraped_data.get('location', 'N/A')}
        
        Provide a comprehensive summary that captures:
        1. Main interests and hobbies (even if inferred from context)
        2. Travel preferences (if mentioned, or infer from location)
        3. Social behavior patterns
        4. Activity preferences (outdoor, cultural, food, etc.)
        5. Personality indicators
        
        If information is limited, make reasonable inferences based on:
        - Location context (Bacolod = food, festivals, culture)
        - Tourism app usage (suggests travel interest)
        - Any available data points
        
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
        You are analyzing a personality summary to extract travel-related personality trait scores.
        
        CRITICAL: Read the summary carefully and extract specific personality indicators. 
        Do NOT use default 0.5 scores - assign scores based on what the summary actually says.
        
        Personality Summary:
        {summary}
        
        Based on the summary above, assign scores (0.0 to 1.0) for each trait:
        
        1. **adventurous** (0.0-1.0): 
           - Look for: mentions of sports, outdoor activities, adventure, exploration, travel, active lifestyle
           - If summary mentions: "sports", "athlete", "active", "adventure", "exploration" → score 0.7-0.9
           - If summary mentions: "travel", "exploring" → score 0.6-0.8
           - If no mention → score 0.5-0.6 (moderate for tourism app user)
        
        2. **cultural** (0.0-1.0):
           - Look for: mentions of festivals, arts, traditions, cultural experiences, museums, local culture
           - If summary mentions: "cultural", "festivals", "arts", "traditions" → score 0.7-0.9
           - If location is Bacolod (known for culture) → score 0.6-0.8
           - If no mention → score 0.5-0.6
        
        3. **foodie** (0.0-1.0):
           - Look for: mentions of food, restaurants, culinary, dining, cuisine
           - If summary mentions: "food", "culinary", "restaurants" → score 0.7-0.9
           - If location is Bacolod (known for food) → score 0.6-0.8
           - If no mention → score 0.5-0.6
        
        4. **nature_lover** (0.0-1.0):
           - Look for: mentions of beaches, mountains, parks, nature, outdoor scenery
           - If summary mentions: "beaches", "mountains", "parks", "nature" → score 0.7-0.9
           - If summary mentions: "outdoor activities" → score 0.6-0.8
           - If no mention → score 0.4-0.5
        
        5. **history_buff** (0.0-1.0):
           - Look for: mentions of history, historical sites, architecture, heritage, museums
           - If summary mentions: "history", "historical", "architecture", "heritage" → score 0.7-0.9
           - If professional role involves law/culture → score 0.5-0.7
           - If no mention → score 0.4-0.5
        
        6. **social** (0.0-1.0):
           - Look for: mentions of social media presence, community engagement, gatherings, events, followers
           - If summary mentions: "social media", "active presence", "community", "followers" → score 0.7-0.9
           - If summary mentions: "sociable", "outgoing", "engaging" → score 0.7-0.9
           - If no mention → score 0.5-0.6
        
        IMPORTANT RULES:
        - Read the summary and extract actual indicators - do NOT default to 0.5
        - If the summary explicitly mentions a trait (e.g., "adventurous", "sociable"), assign 0.7-0.9
        - If the summary implies a trait (e.g., "sports" → adventurous), assign 0.6-0.8
        - If the summary has no mention, use 0.4-0.6 (not 0.5 for all)
        - Vary the scores based on what's in the summary - they should NOT all be the same
        
        Return ONLY valid JSON (no markdown, no code blocks):
        {{
            "adventurous": <score based on summary>,
            "cultural": <score based on summary>,
            "foodie": <score based on summary>,
            "nature_lover": <score based on summary>,
            "history_buff": <score based on summary>,
            "social": <score based on summary>,
            "reasoning": "Brief explanation of how you extracted scores from the summary"
        }}
        
        Example: If summary says "sociable, active in sports, enjoys cultural festivals"
        → adventurous: 0.8, cultural: 0.8, social: 0.9, foodie: 0.6, nature_lover: 0.5, history_buff: 0.5
        """
        
        try:
            logger.info(f"🔍 Analyzing personality from summary (length: {len(summary)} chars)")
            logger.debug(f"   Summary preview: {summary[:200]}...")
            
            response = await self.llm.ainvoke(analysis_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            logger.debug(f"   LLM raw response: {content[:500]}")
            
            # Parse JSON response
            # Try to extract JSON from response (handle markdown code blocks)
            content = content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Try to find JSON object in the response
            import re
            json_match = re.search(r'\{[^{}]*"adventurous"[^{}]*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            personality_json = json.loads(content)
            logger.info(f"✅ Parsed personality JSON: {personality_json}")
            
            # Validate and clamp scores to 0.0-1.0 range
            def clamp_score(score, default=0.5):
                try:
                    score = float(score)
                    if score < 0.0 or score > 1.0:
                        logger.warning(f"   Score {score} out of range, clamping to 0.0-1.0")
                        score = max(0.0, min(1.0, score))
                    return score
                except (ValueError, TypeError):
                    logger.warning(f"   Invalid score {score}, using default {default}")
                    return default
            
            traits = PersonalityTraits(
                adventurous=clamp_score(personality_json.get("adventurous", 0.5)),
                cultural=clamp_score(personality_json.get("cultural", 0.5)),
                foodie=clamp_score(personality_json.get("foodie", 0.5)),
                nature_lover=clamp_score(personality_json.get("nature_lover", 0.5)),
                history_buff=clamp_score(personality_json.get("history_buff", 0.5)),
                social=clamp_score(personality_json.get("social", 0.5))
            )
            
            # Check if all traits are zero (likely an error)
            trait_dict = traits.model_dump()
            if all(v == 0.0 for v in trait_dict.values()):
                logger.warning(f"⚠️  All personality traits are 0.0 - likely LLM error, using moderate defaults")
                # Use moderate defaults instead of zeros
                return PersonalityTraits(
                    adventurous=0.6,
                    cultural=0.6,
                    foodie=0.6,
                    nature_lover=0.5,
                    history_buff=0.5,
                    social=0.7
                )
            
            logger.info(f"✅ Personality analysis complete: {traits.model_dump()}")
            return traits
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing personality JSON: {e}")
            logger.error(f"   Content that failed to parse: {content[:500]}")
            # Fallback to moderate personality instead of all zeros
            logger.info("   Using moderate default personality scores")
            return PersonalityTraits(
                adventurous=0.6,
                cultural=0.6,
                foodie=0.6,
                nature_lover=0.5,
                history_buff=0.5,
                social=0.7
            )
        except Exception as e:
            logger.error(f"❌ Error analyzing personality: {e}", exc_info=True)
            logger.info("   Using moderate default personality scores")
            return PersonalityTraits(
                adventurous=0.6,
                cultural=0.6,
                foodie=0.6,
                nature_lover=0.5,
                history_buff=0.5,
                social=0.7
            )

    async def summarize_google_search_results(
        self,
        search_results: Dict[str, Any],
        first_name: str,
        last_name: str
    ) -> str:
        """
        Summarize Google search results using LLM to extract personality information
        """
        # Extract search result snippets
        results = search_results.get("results", [])
        if not results:
            return f"No search results found for {first_name} {last_name}."
        
        # Build context from search results
        search_context = []
        for idx, result in enumerate(results[:10], 1):  # Use top 10 results
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            url = result.get("url", "")
            search_context.append(f"{idx}. {title}\n   {snippet}\n   URL: {url}")
        
        summary_prompt = f"""
        Analyze the following Google search results for "{first_name} {last_name}" 
        and create a comprehensive personality profile based on the information found.
        
        IMPORTANT: Even if the search results contain limited information, you MUST extract 
        personality indicators from what is available. Do NOT say "lack of information" or 
        "insufficient data" - instead, infer personality traits from:
        - Job titles and professional roles
        - Location mentions
        - Any activities, interests, or affiliations mentioned
        - Social media presence patterns
        - News articles or public records
        
        Search Results:
        {chr(10).join(search_context)}
        
        Extract and summarize:
        1. Main interests, hobbies, and activities mentioned (even if inferred)
        2. Travel preferences and destinations (if any, or infer from location/context)
        3. Social behavior patterns (professional, social media presence, etc.)
        4. Activity preferences (outdoor, cultural, food, sports, etc.)
        5. Personality indicators (adventurous, cultural, foodie, nature lover, etc.)
        6. Any other relevant information about their lifestyle and preferences
        
        Focus on information that would help understand their travel and tourism preferences.
        If specific information is limited, make reasonable inferences based on:
        - Their location (Bacolod, Philippines - known for food, festivals, culture)
        - Their use of a tourism app (suggests travel interest)
        - Any professional or social affiliations mentioned
        
        Provide a positive, constructive summary that highlights personality traits that can be 
        inferred or reasonably assumed from the available information. Do NOT focus on what's missing.
        
        Summary:
        """
        
        try:
            response = await self.llm.ainvoke(summary_prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"Error summarizing Google search results: {e}")
            return f"Unable to analyze Google search results for {first_name} {last_name}."

    async def analyze_personality_from_google_search(
        self,
        first_name: str,
        last_name: str,
        search_results: Dict[str, Any]
    ) -> PersonalityTraits:
        """
        Analyze personality from Google search results
        """
        # First, summarize the search results
        summary = await self.summarize_google_search_results(search_results, first_name, last_name)
        
        # Then analyze personality from the summary
        return await self.analyze_personality_from_summary(summary)
