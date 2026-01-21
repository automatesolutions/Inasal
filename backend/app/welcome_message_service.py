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
        """Get top 2-3 personality traits"""
        traits = {
            "adventurous": personality.adventurous,
            "cultural": personality.cultural,
            "foodie": personality.foodie,
            "nature_lover": personality.nature_lover,
            "history_buff": personality.history_buff,
            "social": personality.social
        }
        sorted_traits = sorted(traits.items(), key=lambda x: x[1], reverse=True)
        top_2 = sorted_traits[:2]
        return [f"{trait} ({score:.1f})" for trait, score in top_2]

    async def generate_welcome_message(
        self,
        user_name: str,
        personality: PersonalityTraits
    ) -> str:
        """
        Generate personalized welcome message mentioning user's personality
        """
        # Identify top personality traits
        top_traits = self._get_top_traits(personality)
        top_traits_text = ", ".join(top_traits) if top_traits else "exploring new places"
        
        welcome_prompt = f"""
        You are MOGI, a friendly puppet mascot guide for Bacolod, Philippines.
        
        Generate a warm, personalized welcome message for {user_name} that:
        1. Introduces yourself as MOGI
        2. Mentions their personality traits: {top_traits_text}
        3. Explains that you've prepared personalized recommendations
        4. Invites them to explore the recommendations or ask questions
        
        Keep it friendly, enthusiastic, and conversational (can use Filipino-English mix like "Kumusta!").
        Maximum 3-4 sentences.
        
        Welcome Message:
        """
        
        try:
            response = await self.llm.ainvoke(welcome_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip()
        except Exception as e:
            logger.error(f"Error generating welcome message: {e}")
            # Fallback welcome message
            return f"Kumusta {user_name}! I'm MOGI, your friendly guide to Bacolod! 🎭 I'm here to help you discover amazing places - from delicious inasal spots to hidden beaches. What would you like to explore today?"

    def format_personality_summary(
        self,
        personality: PersonalityTraits
    ) -> str:
        """Format personality summary for display"""
        traits = {
            "Adventurous": personality.adventurous,
            "Cultural": personality.cultural,
            "Foodie": personality.foodie,
            "Nature Lover": personality.nature_lover,
            "History Buff": personality.history_buff,
            "Social": personality.social
        }
        
        # Get top 3 traits
        sorted_traits = sorted(traits.items(), key=lambda x: x[1], reverse=True)
        top_3 = sorted_traits[:3]
        
        summary_parts = []
        for trait, score in top_3:
            if score > 0.6:
                summary_parts.append(f"{trait} ({score:.0%})")
        
        if summary_parts:
            return f"Your top interests: {', '.join(summary_parts)}"
        else:
            return "We're still learning about your interests. Let's explore together!"
