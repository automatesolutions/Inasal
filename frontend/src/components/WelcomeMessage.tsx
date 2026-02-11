"use client";

import Image from "next/image";
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
    secret_spots: any[];
  };
  personality_summary: string;
}

export function WelcomeMessage({ content, recommendations, personality_summary }: WelcomeMessageProps) {
  return (
    <div className="welcome-message bg-gradient-to-br from-amber-50 to-orange-50 rounded-lg p-6 mb-4">
      {/* MOGI Avatar */}
      <div className="flex items-start gap-4 mb-4">
        <div className="w-16 h-16 rounded-full overflow-hidden flex items-center justify-center bg-amber-400 flex-shrink-0">
          <Image
            src="/Image2.png"
            alt="MOGI"
            width={64}
            height={64}
            className="w-full h-full object-cover"
          />
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
        {/* Debug: Log recommendations count */}
        {console.log("Recommendations received:", {
          secret_spots: recommendations.secret_spots?.length || 0,
          hotels: recommendations.hotels?.length || 0,
          restaurants: recommendations.restaurants?.length || 0,
          tourist_spots: recommendations.tourist_spots?.length || 0,
          beaches: recommendations.beaches?.length || 0,
          total: Object.values(recommendations).reduce((sum, arr) => sum + (Array.isArray(arr) ? arr.length : 0), 0)
        })}
        
        {/* Tourist Spots - First */}
        {recommendations.tourist_spots && recommendations.tourist_spots.length > 0 && (
          <RecommendationCategory
            title="Tourist Spots"
            icon="📍"
            items={recommendations.tourist_spots}
          />
        )}
        
        {/* Hotels */}
        {recommendations.hotels && recommendations.hotels.length > 0 && (
          <RecommendationCategory
            title="Hotels"
            icon="🏨"
            items={recommendations.hotels}
          />
        )}
        
        {/* Restaurants */}
        {recommendations.restaurants && recommendations.restaurants.length > 0 && (
          <RecommendationCategory
            title="Restaurants"
            icon="🍽️"
            items={recommendations.restaurants}
          />
        )}
        
        {/* Beaches */}
        {recommendations.beaches && recommendations.beaches.length > 0 && (
          <RecommendationCategory
            title="Beaches"
            icon="🏖️"
            items={recommendations.beaches}
          />
        )}
        
        {/* Mountains */}
        {recommendations.mountains && recommendations.mountains.length > 0 && (
          <RecommendationCategory
            title="Mountains"
            icon="⛰️"
            items={recommendations.mountains}
          />
        )}
        
        {/* Resorts */}
        {recommendations.resorts && recommendations.resorts.length > 0 && (
          <RecommendationCategory
            title="Resorts"
            icon="🏖️"
            items={recommendations.resorts}
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
        
        {/* Scams and Danger Zones - Link to separate page */}
        {recommendations.places_to_avoid && recommendations.places_to_avoid.length > 0 && (
          <div className="bg-gradient-to-r from-red-50 to-orange-50 border-2 border-red-200 rounded-lg p-6 mb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-orange-500 rounded-xl flex items-center justify-center text-2xl">
                  ⚠️
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900 mb-1">
                    ⚠️ Scams and Danger Zones in Bacolod
                  </h3>
                  <p className="text-sm text-gray-600">
                    {recommendations.places_to_avoid.length} safety alert{recommendations.places_to_avoid.length !== 1 ? 's' : ''} available
                  </p>
                </div>
              </div>
              <a
                href="/safety"
                className="px-6 py-3 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 transition-colors flex items-center gap-2"
              >
                View Safety Information
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </a>
            </div>
          </div>
        )}
        
        {/* Secret Spot - Last (Profile-based, unique) */}
        {recommendations.secret_spots && recommendations.secret_spots.length > 0 && (
          <RecommendationCategory
            title="🔐 Secret Spot (Just for You)"
            icon="🔐"
            items={recommendations.secret_spots}
            isSecretSpot={true}
          />
        )}
        
        {/* Show message if no recommendations */}
        {Object.values(recommendations).every(arr => !Array.isArray(arr) || arr.length === 0) && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
            <p className="text-yellow-800 text-sm">
              <strong>No recommendations available yet.</strong> This might be because:
            </p>
            <ul className="text-yellow-700 text-xs mt-2 list-disc list-inside text-left max-w-md mx-auto">
              <li>Recommendation engine is still initializing</li>
              <li>No data available in the recommendation database</li>
              <li>Personality analysis is still in progress</li>
            </ul>
            <p className="text-yellow-800 text-sm mt-2">
              Try asking MOGI directly about places to visit in Bacolod!
            </p>
          </div>
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
