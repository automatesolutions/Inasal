"""Complete pipeline: Search → Scrape → Summarize → Analyze → Store"""

import logging
from typing import Optional
from datetime import datetime
from app.social_scraper import SocialMediaScraper
from app.personality_analyzer import PersonalityAnalyzer
from app.user_profile import UserProfileService, PersonalityTraits

logger = logging.getLogger(__name__)
profile_service = UserProfileService()


async def analyze_personality_from_social_media(
    user_id: str,
    first_name: str,
    last_name: str,
    phone_number: Optional[str] = None
) -> bool:
    """
    Complete pipeline: Search → Scrape → Summarize → Analyze → Store
    
    Returns True if successful, False otherwise
    """
    try:
        logger.info(f"Starting personality analysis for {first_name} {last_name} ({user_id})")
        
        # Step 1: Search for social profiles
        scraper = SocialMediaScraper()
        search_results = await scraper.search_social_profiles(
            first_name, last_name, phone_number
        )
        
        # Step 2: Scrape profile data (try Facebook first, then Instagram)
        scraped_data = None
        if search_results.get("facebook_profiles"):
            profile_url = search_results["facebook_profiles"][0].get("url")
            if profile_url:
                scraped_data = await scraper.scrape_profile_data(
                    profile_url, "facebook"
                )
        
        if not scraped_data and search_results.get("instagram_profiles"):
            profile_url = search_results["instagram_profiles"][0].get("url")
            if profile_url:
                scraped_data = await scraper.scrape_profile_data(
                    profile_url, "instagram"
                )
        
        if not scraped_data:
            # No profile found, use default personality
            logger.info(f"No social profile found for {first_name} {last_name}, using default personality")
            await profile_service.update_personality(
                user_id, PersonalityTraits()
            )
            
            return False
        
        # Step 3: Summarize scraped data
        analyzer = PersonalityAnalyzer()
        summary = await analyzer.summarize_social_data(scraped_data)
        
        # Step 4: Analyze personality from summary
        personality = await analyzer.analyze_personality_from_summary(summary)
        
        # Step 5: Store personality and summary
        await profile_service.update_personality(user_id, personality)
        
        logger.info(f"✅ Personality analysis completed for {user_id}")
        logger.info(f"   Personality scores: {personality.model_dump()}")
        return True
        
    except Exception as e:
        logger.error(f"Error analyzing personality for {user_id}: {e}", exc_info=True)
        # Use default personality on error
        try:
            await profile_service.update_personality(
                user_id, PersonalityTraits()
            )
        except Exception as update_error:
            logger.error(f"Failed to set default personality: {update_error}")
        return False
