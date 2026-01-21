"use client";

import { RecommendationCategory } from "./RecommendationCategory";

interface WelcomeMessageProps {
  content: string;
  recommendations: {
    hotels: any[];
    restaurants: any[];
    accommodations: any[];
    tourist_spots: any[];
    beaches: any[];
    mountains: any[];
    resorts: any[];
    places_to_avoid: any[];
    businesses: any[];
    events: any[];
    hidden_gems: any[];
  };
  personality_summary: string;
}

export function WelcomeMessage({ content, recommendations, personality_summary }: WelcomeMessageProps) {
  return (
    <div className="welcome-message bg-gradient-to-br from-amber-50 to-orange-50 rounded-lg p-6 mb-4">
      {/* MOGI Avatar Placeholder */}
      <div className="flex items-start gap-4 mb-4">
        <div className="w-16 h-16 bg-amber-400 rounded-full flex items-center justify-center text-3xl flex-shrink-0">
          🎭
        </div>
        <div className="flex-1">
          <h2 className="text-xl font-bold text-amber-900 mb-2">MOGI</h2>
          <div className="text-gray-700 whitespace-pre-wrap">{content}</div>
        </div>
      </div>
      
      {/* Personality Summary */}
      {personality_summary && (
        <div className="bg-white/60 rounded-lg p-4 mb-4">
          <h3 className="font-semibold text-amber-900 mb-1">Your Personality Profile</h3>
          <p className="text-sm text-gray-700">{personality_summary}</p>
        </div>
      )}
      
      {/* Recommendations by Category */}
      <div className="recommendations-grid mt-6">
        {recommendations.hidden_gems && recommendations.hidden_gems.length > 0 && (
          <RecommendationCategory
            title="✨ Hidden Gems"
            icon="💎"
            items={recommendations.hidden_gems}
            isHiddenGem={true}
          />
        )}
        
        {recommendations.hotels && recommendations.hotels.length > 0 && (
          <RecommendationCategory
            title="Hotels"
            icon="🏨"
            items={recommendations.hotels}
          />
        )}
        
        {recommendations.restaurants && recommendations.restaurants.length > 0 && (
          <RecommendationCategory
            title="Restaurants"
            icon="🍽️"
            items={recommendations.restaurants}
          />
        )}
        
        {recommendations.beaches && recommendations.beaches.length > 0 && (
          <RecommendationCategory
            title="Beaches"
            icon="🏖️"
            items={recommendations.beaches}
          />
        )}
        
        {recommendations.mountains && recommendations.mountains.length > 0 && (
          <RecommendationCategory
            title="Mountains"
            icon="⛰️"
            items={recommendations.mountains}
          />
        )}
        
        {recommendations.resorts && recommendations.resorts.length > 0 && (
          <RecommendationCategory
            title="Resorts"
            icon="🏖️"
            items={recommendations.resorts}
          />
        )}
        
        {recommendations.tourist_spots && recommendations.tourist_spots.length > 0 && (
          <RecommendationCategory
            title="Tourist Spots"
            icon="📍"
            items={recommendations.tourist_spots}
          />
        )}
        
        {recommendations.accommodations && recommendations.accommodations.length > 0 && (
          <RecommendationCategory
            title="Accommodations"
            icon="🛏️"
            items={recommendations.accommodations}
          />
        )}
        
        {recommendations.events && recommendations.events.length > 0 && (
          <RecommendationCategory
            title="Events"
            icon="🎪"
            items={recommendations.events}
          />
        )}
        
        {recommendations.businesses && recommendations.businesses.length > 0 && (
          <RecommendationCategory
            title="Businesses Nearby"
            icon="🏢"
            items={recommendations.businesses}
          />
        )}
        
        {recommendations.places_to_avoid && recommendations.places_to_avoid.length > 0 && (
          <RecommendationCategory
            title="⚠️ Places to Avoid"
            icon="⚠️"
            items={recommendations.places_to_avoid}
          />
        )}
      </div>
      
      {/* Call to Action */}
      <div className="mt-6 p-4 bg-amber-100 rounded-lg text-center">
        <p className="text-amber-900 font-medium">
          Click any link to learn more, or ask me anything about Bacolod!
        </p>
      </div>
    </div>
  );
}
