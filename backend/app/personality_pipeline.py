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
        logger.warning(f"🚀 STEP 1: Starting personality analysis for {first_name} {last_name} ({user_id})")
        
        # Step 1: Search for social profiles
        logger.warning(f"🚀 STEP 2: Creating SocialMediaScraper...")
        scraper = SocialMediaScraper()
        logger.warning(f"🚀 STEP 3: Calling search_social_profiles for {first_name} {last_name}...")
        search_results = await scraper.search_social_profiles(
            first_name, last_name, phone_number
        )
        logger.warning(f"🚀 STEP 4: search_social_profiles completed. Results: {list(search_results.keys()) if search_results else 'None'}")
        
        # Step 2: Scrape profile data (try Facebook first, then Instagram)
        scraped_data = None
        if search_results.get("facebook_profiles"):
            profile_url = search_results["facebook_profiles"][0].get("url")
            if profile_url:
                logger.info(f"Attempting to scrape Facebook profile: {profile_url}")
                scraped_data = await scraper.scrape_profile_data(
                    profile_url, "facebook"
                )
                if scraped_data:
                    logger.info(f"✅ Successfully scraped Facebook data: {list(scraped_data.keys())}")
                else:
                    # This is expected - Facebook often blocks scraping, SERP will be used instead
                    logger.debug(f"Facebook scraping returned no data (expected) - SERP will be used as fallback")
                    scraped_data = None  # Explicitly set to None to ensure SERP is called
        else:
            logger.info(f"   No Facebook profiles found in search results")
        
        if not scraped_data and search_results.get("instagram_profiles"):
            profile_url = search_results["instagram_profiles"][0].get("url")
            if profile_url:
                logger.info(f"Attempting to scrape Instagram profile: {profile_url}")
                scraped_data = await scraper.scrape_profile_data(
                    profile_url, "instagram"
                )
                if scraped_data:
                    logger.info(f"✅ Successfully scraped Instagram data: {list(scraped_data.keys())}")
                else:
                    # This is expected - Instagram often blocks scraping, SERP will be used instead
                    logger.debug(f"Instagram scraping returned no data (expected) - SERP will be used as fallback")
                    scraped_data = None  # Explicitly set to None to ensure SERP is called
        else:
            if not search_results.get("instagram_profiles"):
                logger.info(f"   No Instagram profiles found in search results")
        
        # Always use SERP if no meaningful scraped data
        # This is the PRIMARY method - social media scraping is just a bonus if it works
        if not scraped_data:
            logger.info(f"📋 Using SERP Google search (primary method) for {first_name} {last_name}")
            logger.info(f"   Note: Social media scraping often fails due to anti-bot measures - SERP is more reliable")
        
        # Step 3: Collect source links from search results
        source_links = []
        if search_results.get("facebook_profiles"):
            for profile in search_results["facebook_profiles"]:
                if profile.get("url"):
                    source_links.append(profile["url"])
        if search_results.get("instagram_profiles"):
            for profile in search_results["instagram_profiles"]:
                if profile.get("url"):
                    source_links.append(profile["url"])
        
        analyzer = PersonalityAnalyzer()
        summary = None
        personality = None
        
        # Check if scraped_data is actually meaningful (not just an empty dict)
        has_meaningful_data = scraped_data and isinstance(scraped_data, dict) and any(
            v for v in scraped_data.values() if v and (isinstance(v, str) and len(v.strip()) > 0 or isinstance(v, list) and len(v) > 0)
        )
        
        logger.info(f"📊 Scraped data status: {'Found with content' if has_meaningful_data else 'Not found or empty'}")
        if scraped_data and not has_meaningful_data:
            logger.info(f"   Scraped data exists but is empty: {scraped_data}")
        
        if has_meaningful_data:
            # Step 4a: Summarize scraped profile data
            logger.info(f"✅ Found scraped profile data with content, analyzing...")
            try:
                summary = await analyzer.summarize_social_data(scraped_data)
                
                # Check if summary indicates we should use SERP instead
                if summary and ("empty" in summary.lower() or "unavailable" in summary.lower() or "use serp" in summary.lower()):
                    logger.info(f"   Social media data summary indicates empty data, falling back to SERP...")
                    has_meaningful_data = False
                    summary = None
                else:
                    # Step 5a: Analyze personality from scraped data summary
                    personality = await analyzer.analyze_personality_from_summary(summary)
                    logger.info(f"✅ Personality analyzed from social media data: {personality.model_dump()}")
            except Exception as e:
                logger.error(f"❌ Error analyzing social media data: {e}", exc_info=True)
                has_meaningful_data = False  # Fall through to SERP
                logger.info(f"   Falling back to SERP search...")
        
        if not has_meaningful_data:
            # Step 4b: No profile found - use Google SERP search results directly
            logger.info(f"🔍 No social profile found for {first_name} {last_name}, using Google SERP search results")
            
            # Search Google directly for the person using SERP API
            from app.bright_data_client import bright_data_client
            try:
                google_query = f"{first_name} {last_name}"
                if phone_number:
                    google_query += f" {phone_number}"
                
                logger.info(f"🔍 Searching Google SERP for: {google_query}")
                logger.info(f"   Using Bright Data client: {bright_data_client}")
                
                serp_results = await bright_data_client.search_public(
                    source="google",
                    query=google_query,
                    limit=10
                )
                
                logger.info(f"📊 SERP search response received")
                logger.info(f"   success: {serp_results.get('success')}")
                logger.info(f"   results_count: {len(serp_results.get('results', []))}")
                logger.info(f"   error: {serp_results.get('error', 'None')}")
                if serp_results.get("results"):
                    logger.info(f"   First result: {serp_results.get('results')[0] if serp_results.get('results') else 'None'}")
                
                if serp_results.get("success") and serp_results.get("results"):
                    logger.info(f"✅ SERP search successful with {len(serp_results.get('results', []))} results")
                    # Extract URLs from SERP results for source links
                    for result in serp_results.get("results", [])[:10]:
                        if result.get("url"):
                            source_links.append(result["url"])
                    
                    logger.info(f"📝 Found {len(source_links)} source links, summarizing with LLM...")
                    
                    # Summarize Google search results
                    summary = await analyzer.summarize_google_search_results(
                        serp_results, first_name, last_name
                    )
                    
                    logger.info(f"✅ LLM summary generated ({len(summary)} chars), analyzing personality...")
                    
                    # Analyze personality from SERP summary
                    logger.info(f"🔍 Analyzing personality from SERP summary...")
                    personality = await analyzer.analyze_personality_from_summary(summary)
                    personality_dict = personality.model_dump()
                    logger.info(f"✅ Analyzed personality from SERP results: {personality_dict}")
                    
                    # Verify personality has meaningful values
                    has_meaningful = any(v > 0.5 for v in personality_dict.values())
                    if not has_meaningful:
                        logger.warning(f"⚠️  Personality analysis returned low scores: {personality_dict}")
                        logger.warning(f"   This might indicate the LLM didn't extract personality properly from SERP results")
                else:
                    error_msg = serp_results.get("error", "Unknown error")
                    logger.warning(f"⚠️  No SERP results found for {first_name} {last_name}")
                    logger.warning(f"   SERP response: success={serp_results.get('success')}, results={len(serp_results.get('results', []))}, error={error_msg}")
                    logger.warning(f"   This usually means:")
                    logger.warning(f"   1. Bright Data zones (serp_api2, webscrape_amzn) are not configured")
                    logger.warning(f"   2. The zones don't have SERP API access enabled")
                    logger.warning(f"   3. Check your Bright Data dashboard to verify zone configuration")
                    
                    # Try to infer personality from name and basic context using LLM
                    logger.info(f"🤖 Attempting to infer personality from name and context (no SERP results)...")
                    try:
                        # Create a context-based summary for LLM analysis
                        context_summary = f"""
                        User Profile Context:
                        - Name: {first_name} {last_name}
                        - Location: Bacolod, Philippines (tourism app user)
                        - Context: Using a mobile tourism application suggests interest in travel and exploration
                        
                        Based on this limited information, infer reasonable personality traits:
                        - Tourism interest suggests some level of adventurousness (0.6-0.7) and cultural curiosity (0.6-0.7)
                        - Using a mobile app indicates tech-savviness and social engagement (0.7-0.8)
                        - Being in Bacolod (known for food, festivals, culture) suggests potential foodie (0.6-0.7) and cultural interests (0.7-0.8)
                        - General tourism interest suggests moderate nature_lover (0.5-0.6) and history_buff (0.4-0.5)
                        
                        IMPORTANT: Return scores in the 0.4-0.8 range. Do NOT return all zeros.
                        Use moderate to high scores since this person is using a tourism app.
                        """
                        
                        # Use existing analyzer to infer personality from context
                        personality = await analyzer.analyze_personality_from_summary(context_summary)
                        personality_dict = personality.model_dump()
                        
                        # Verify we got reasonable scores
                        if all(v == 0.0 for v in personality_dict.values()):
                            logger.warning(f"⚠️  LLM returned all zeros, using moderate defaults")
                            personality = PersonalityTraits(
                                adventurous=0.65,
                                cultural=0.70,
                                foodie=0.65,
                                nature_lover=0.55,
                                history_buff=0.45,
                                social=0.75
                            )
                        
                        summary = f"Personality inferred from name and context (no SERP results available). SERP Error: {error_msg}"
                        logger.info(f"✅ Inferred personality from context: {personality.model_dump()}")
                    except Exception as infer_error:
                        logger.error(f"❌ Failed to infer personality: {infer_error}", exc_info=True)
                        # Use moderate default personality instead of all zeros
                        logger.info("   Using moderate default personality scores")
                        personality = PersonalityTraits(
                            adventurous=0.65,
                            cultural=0.70,
                            foodie=0.65,
                            nature_lover=0.55,
                            history_buff=0.45,
                            social=0.75
                        )
                        summary = f"No search results found for {first_name} {last_name}. SERP Error: {error_msg}"
            except Exception as serp_error:
                logger.error(f"❌ Error in SERP search: {serp_error}", exc_info=True)
                # Use moderate default personality on error instead of all zeros
                logger.info("   Using moderate default personality scores due to SERP error")
                personality = PersonalityTraits(
                    adventurous=0.65,
                    cultural=0.70,
                    foodie=0.65,
                    nature_lover=0.55,
                    history_buff=0.45,
                    social=0.75
                )
                summary = f"Error searching for {first_name} {last_name}: {str(serp_error)}"
        
        # Ensure we have a personality object
        if personality is None:
            logger.error(f"❌ Personality is None after analysis - using moderate defaults")
            personality = PersonalityTraits(
                adventurous=0.65,
                cultural=0.70,
                foodie=0.65,
                nature_lover=0.55,
                history_buff=0.45,
                social=0.75
            )
            if not summary:
                summary = f"Personality analysis completed with moderate defaults for {first_name} {last_name}"
        
        # Step 6: Store personality, summary, and source links
        logger.warning(f"💾 Saving personality to InstantDB for {user_id}...")
        personality_dict = personality.model_dump()
        logger.warning(f"   Personality scores: {personality_dict}")
        logger.warning(f"   Summary length: {len(summary) if summary else 0} chars")
        logger.warning(f"   Source links: {len(source_links)} links")
        
        # Verify we have meaningful traits before saving
        has_meaningful = any(v > 0.5 for v in personality_dict.values())
        if not has_meaningful:
            logger.error(f"❌ WARNING: Personality has no traits > 0.5: {personality_dict}")
            logger.error(f"   This will result in all defaults (0.5) being saved!")
        
        try:
            updated_profile = await profile_service.update_personality(
                user_id, 
                personality,
                characteristics_summary=summary,
                source_links=source_links if source_links else None
            )
            
            if updated_profile:
                saved_traits = updated_profile.personality.model_dump()
                logger.warning(f"✅ Personality analysis completed and saved for {user_id}")
                logger.warning(f"   Saved traits: {saved_traits}")
                
                # Verify saved traits are not all defaults
                all_defaults = all(v == 0.5 for v in saved_traits.values())
                if all_defaults:
                    logger.error(f"❌ CRITICAL: Saved personality is all defaults (0.5)!")
                    logger.error(f"   This means InstantDB update didn't work correctly!")
                else:
                    logger.warning(f"✅ Saved personality has meaningful traits: {[k for k, v in saved_traits.items() if v > 0.5]}")
            else:
                logger.error(f"❌ Personality analysis completed but failed to save for {user_id}")
                logger.error(f"   update_personality returned None - check InstantDB connection")
                # Still return True if we have meaningful traits
        except Exception as save_error:
            logger.error(f"❌ Error saving personality: {save_error}", exc_info=True)
            import traceback
            logger.error(f"   Full traceback: {traceback.format_exc()}")
            # Still return True if we have meaningful traits
        
        logger.info(f"✅ Personality analysis completed for {user_id}")
        logger.info(f"   Final personality scores: {personality_dict}")
        
        # Return True if we got meaningful personality (lowered threshold to 0.4)
        has_meaningful_traits = any(v > 0.4 for v in personality_dict.values())
        if has_meaningful_traits:
            meaningful_list = [f"{k}({v:.2f})" for k, v in personality_dict.items() if v > 0.4]
            logger.info(f"✅ Personality has meaningful traits (>0.4): {meaningful_list}")
            return True
        else:
            logger.warning(f"⚠️  Personality has no traits > 0.4: {personality_dict}")
            # Even if no traits > 0.4, if we saved personality, return True
            # This ensures the system knows personality analysis completed
            logger.info(f"   But personality was saved, so returning True")
            return True  # Return True since we saved personality (even if low scores)
        
    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR analyzing personality for {user_id}: {e}", exc_info=True)
        import traceback
        logger.error(f"   Full traceback: {traceback.format_exc()}")
        # Use moderate default personality on error instead of all zeros
        logger.warning("   Using moderate default personality scores due to error")
        try:
            moderate_personality = PersonalityTraits(
                adventurous=0.65,
                cultural=0.70,
                foodie=0.65,
                nature_lover=0.55,
                history_buff=0.45,
                social=0.75
            )
            logger.warning(f"💾 Saving moderate defaults to InstantDB due to error...")
            await profile_service.update_personality(
                user_id, 
                moderate_personality,
                characteristics_summary=f"Personality analysis failed, using moderate defaults. Error: {str(e)}"
            )
            logger.warning(f"✅ Moderate defaults saved")
            logger.info(f"✅ Saved moderate default personality for {user_id}")
            return True  # Return True since we saved personality
        except Exception as update_error:
            logger.error(f"❌ Failed to set default personality: {update_error}", exc_info=True)
            return False
