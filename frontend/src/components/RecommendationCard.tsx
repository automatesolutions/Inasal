"use client";

interface RecommendationCardProps {
  recommendation: {
    id?: string;
    name: string;
    description: string;
    links?: {
      details?: string;
      map?: string;
      directions?: string;
      booking?: string;
      website?: string;
      official?: string;
    };
    match_score?: number;
    image?: string;
    why_secret?: string;
    hidden_trait_match?: string;
    rating?: number;
    price_range?: string;
    address?: string;
    type?: string;
    area?: string;
    advice?: string;
  };
  isHiddenGem?: boolean;
  isSecretSpot?: boolean;
}

export function RecommendationCard({ recommendation, isHiddenGem = false, isSecretSpot = false }: RecommendationCardProps) {
  return (
    <div className={`bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow ${isSecretSpot ? 'border-2 border-purple-400' : isHiddenGem ? 'border-2 border-amber-400' : ''}`}>
      {recommendation.image && (
        <div className="h-48 bg-gray-200 overflow-hidden">
          <img
            src={recommendation.image}
            alt={recommendation.name}
            className="w-full h-full object-cover"
          />
        </div>
      )}
      <div className="p-4">
        <div className="flex items-start justify-between mb-2">
          <h4 className="font-semibold text-lg text-gray-900">{recommendation.name}</h4>
          {isSecretSpot && (
            <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded-full">
              🔐 Secret Spot
            </span>
          )}
          {isHiddenGem && !isSecretSpot && (
            <span className="text-xs bg-amber-100 text-amber-800 px-2 py-1 rounded-full">
              ✨ Hidden Gem
            </span>
          )}
        </div>
        
        <p className="text-sm text-gray-600 mb-3 line-clamp-2">{recommendation.description}</p>
        
        {recommendation.why_secret && (
          <p className="text-xs text-purple-700 italic mb-2">🔐 {recommendation.why_secret}</p>
        )}
        
        {recommendation.advice && (
          <p className="text-xs text-red-700 bg-red-50 p-2 rounded mb-2">
            <strong>⚠️ Safety Advice:</strong> {recommendation.advice}
          </p>
        )}
        
        {recommendation.address && (
          <p className="text-xs text-gray-500 mb-2">📍 {recommendation.address}</p>
        )}
        
        <div className="flex items-center gap-4 mb-3 text-xs text-gray-500">
          {recommendation.match_score !== undefined && (
            <span>Match: {(recommendation.match_score * 100).toFixed(0)}%</span>
          )}
          {recommendation.rating !== undefined && recommendation.rating !== null && (
            <span>⭐ {typeof recommendation.rating === 'number' ? recommendation.rating.toFixed(1) : String(recommendation.rating)}</span>
          )}
          {recommendation.price_range && (
            <span>💰 {recommendation.price_range}</span>
          )}
        </div>
        
        <div className="flex flex-wrap gap-2">
          {recommendation.links?.details && (
            <a
              href={recommendation.links.details}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs bg-amber-600 text-white px-3 py-1 rounded hover:bg-amber-700 transition-colors"
            >
              View Details
            </a>
          )}
          {recommendation.links?.directions && (
            <a
              href={recommendation.links.directions}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 transition-colors"
            >
              Get Directions
            </a>
          )}
          {recommendation.links?.map && (
            <a
              href={recommendation.links.map}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 transition-colors"
            >
              View on Map
            </a>
          )}
          {recommendation.links?.booking && (
            <a
              href={recommendation.links.booking}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 transition-colors"
            >
              Book Now
            </a>
          )}
          {recommendation.links?.website && (
            <a
              href={recommendation.links.website}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs bg-gray-600 text-white px-3 py-1 rounded hover:bg-gray-700 transition-colors"
            >
              Website
            </a>
          )}
          {recommendation.links?.official && (
            <a
              href={recommendation.links.official}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 transition-colors"
            >
              Official Info
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
