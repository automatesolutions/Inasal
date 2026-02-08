"""Welcome message service for MOGI chatbot"""

import logging
from app.llm_factory import get_chat_llm
from app.user_profile import PersonalityTraits

logger = logging.getLogger(__name__)


class WelcomeMessageService:
    """Generate MOGI's welcome message with personality introduction"""

    def __init__(self):
        self.llm = get_chat_llm(temperature=0.7)

    def _get_top_traits(self, personality: PersonalityTraits) -> list:
        """Get top 2-3 personality traits - only if they're above default (0.5)"""
        traits = {
            "adventurous": personality.adventurous,
            "cultural": personality.cultural,
            "foodie": personality.foodie,
            "nature_lover": personality.nature_lover,
            "history_buff": personality.history_buff,
            "social": personality.social
        }
        
        # Filter out traits that are at default (0.5) or below
        meaningful_traits = {k: v for k, v in traits.items() if v > 0.5}
        
        # If no meaningful traits, return empty list
        if not meaningful_traits:
            return []
        
        sorted_traits = sorted(meaningful_traits.items(), key=lambda x: x[1], reverse=True)
        top_2 = sorted_traits[:2]
        return [f"{trait} ({int(score * 100)}%)" for trait, score in top_2]

    async def generate_welcome_message(
        self,
        user_name: str,
        personality: PersonalityTraits
    ) -> str:
        """
        Generate personalized welcome message using LLM with personality context.
        The LLM will intelligently incorporate personality traits if available.
        """
        personality_dict = personality.model_dump()
        logger.info(f"Generating welcome message for {user_name} with personality: {personality_dict}")
        
        # Check if personality has meaningful traits (any > 0.4, lowered from 0.5 to include moderate scores)
        meaningful_traits = {k: v for k, v in personality_dict.items() if v > 0.4}
        
        if meaningful_traits:
            # Include personality context in the prompt
            traits_description = ", ".join(
                [f"{k.replace('_', ' ')}: {int(v * 100)}%" for k, v in meaningful_traits.items()]
            )
            logger.info(f"✅ Using analyzed personality traits: {traits_description}")
            
            prompt = f"""You are MOGI, a friendly puppy mascot guide for Bacolod, Philippines.

Generate a warm, personalized welcome message for {user_name}.

User's personality profile:
{traits_description}

Based on these personality traits, generate a personalized welcome message that:
1. Introduces yourself as MOGI
2. Shows you understand their interests based on their personality
3. Mentions you've prepared personalized recommendations for them
4. Invites them to explore or ask questions

Use a friendly, enthusiastic, conversational tone (you can mix Filipino and English like "Kumusta!").
Keep it to 3-4 sentences maximum.

Welcome Message:"""
        else:
            # No meaningful traits - personality not analyzed yet
            logger.warning(f"⚠️ No meaningful personality traits - generating generic welcome")
            
            prompt = f"""You are MOGI, a friendly puppy mascot guide for Bacolod, Philippines.

Generate a warm welcome message for {user_name} that:
1. Introduces yourself as MOGI
2. Explains you're here to help discover amazing places in Bacolod
3. Mentions you've prepared recommendations
4. Invites them to explore or ask questions

Use a friendly, enthusiastic, conversational tone (you can mix Filipino and English like "Kumusta!").
Keep it to 3-4 sentences maximum.

Welcome Message:"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"✅ LLM generated welcome: {content[:100]}...")
            return content.strip()
        except Exception as e:
            logger.error(f"Error generating welcome message: {e}")
            # Fallback welcome message
            return f"Kumusta {user_name}! I'm MOGI, your friendly puppy mascot guide to Bacolod! 🐾 I'm here to help you discover amazing places - from delicious food to hidden gems. What would you like to explore today?"

    def format_personality_summary(
        self,
        personality: PersonalityTraits
    ) -> str:
        """Format personality summary for display using actual personality data"""
        personality_dict = personality.model_dump()
        logger.warning(f"🔍 Formatting personality summary: {personality_dict}")
        
        # Check if all traits are at default (0.5) - this means analysis hasn't completed
        all_default = all(v == 0.5 for v in personality_dict.values())
        if all_default:
            logger.warning(f"⚠️ All personality traits are at default (0.5) - analysis may not be complete")
            return "We're still learning about your interests. Let's explore together!"
        
        # Filter traits that are above moderate threshold (0.4)
        # Include traits > 0.4 to catch meaningful but moderate scores
        meaningful_traits = {
            k.replace('_', ' ').title(): v 
            for k, v in personality_dict.items() 
            if v > 0.4  # Include traits above 0.4
        }
        
        logger.warning(f"🔍 Meaningful traits (>0.4): {meaningful_traits}")
        
        if not meaningful_traits:
            # No meaningful traits yet
            logger.warning("⚠️ No analyzed traits > 0.4 - returning generic message")
            return "We're still learning about your interests. Let's explore together!"
        
        # Sort by score and get top 3
        sorted_traits = sorted(meaningful_traits.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Format as readable list
        summary_parts = [f"{trait}: {int(score * 100)}%" for trait, score in sorted_traits]
        summary = f"Your top interests: {', '.join(summary_parts)}"
        
        logger.warning(f"✅ Personality summary: {summary}")
        return summary
        
        # Sort by score and get top 3
        sorted_traits = sorted(meaningful_traits.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Format as readable list
        summary_parts = [f"{trait}: {int(score * 100)}%" for trait, score in sorted_traits]
        summary = f"Your top interests: {', '.join(summary_parts)}"
        
        logger.info(f"✅ Personality summary: {summary}")
        return summary
