"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { secretRecommendationsApi, type SecretRecommendation } from "@/lib/api";

export default function SecretRecommendationsPage() {
  const router = useRouter();
  const [secretRecommendations, setSecretRecommendations] = useState<SecretRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadSecretRecommendations();
  }, []);

  const loadSecretRecommendations = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await secretRecommendationsApi.getSecretRecommendations(100);
      setSecretRecommendations(response.data || []);
    } catch (err: any) {
      const errorMessage = err.detail || "Failed to load secret recommendations";
      setError(errorMessage);
      console.error("Error loading secret recommendations:", err);
    } finally {
      setLoading(false);
    }
  };

  const SecretCard = ({ item }: { item: SecretRecommendation }) => {
    return (
      <div className={`bg-white rounded-xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden border-2 ${item.featured ? 'border-purple-500 border-4' : 'border-purple-200'}`}>
        <div className="p-6">
          {item.featured && (
            <div className="mb-3 flex items-center gap-2">
              <span className="px-3 py-1 bg-gradient-to-r from-purple-500 to-pink-500 text-white text-xs font-bold rounded-full">
                ⭐ FEATURED
              </span>
            </div>
          )}
          
          {item.image && (
            <div className="mb-4 rounded-lg overflow-hidden">
              <img
                src={item.image}
                alt={item.name}
                className="w-full h-48 object-cover"
              />
            </div>
          )}
          
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-xl font-bold text-purple-900 flex-1">{item.name}</h3>
            <div className="ml-2 flex flex-col items-end gap-1">
              {item.match_score !== undefined && (
                <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-semibold">
                  {Math.round(item.match_score * 100)}% match
                </span>
              )}
              {item.rating !== undefined && item.rating !== null && (
                <span className="px-2 py-1 bg-amber-100 text-amber-700 rounded text-xs font-semibold">
                  ⭐ {typeof item.rating === 'number' ? item.rating.toFixed(1) : String(item.rating || 'N/A')}
                </span>
              )}
            </div>
          </div>
          
          {item.category && (
            <span className="inline-block mb-2 px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
              {item.category}
            </span>
          )}
          
          <p className="text-gray-600 mb-4 line-clamp-3">{item.description}</p>
          
          {item.tags && item.tags.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-1">
              {item.tags.map((tag, idx) => (
                <span key={idx} className="px-2 py-1 bg-purple-50 text-purple-600 text-xs rounded">
                  #{tag}
                </span>
              ))}
            </div>
          )}
          
          {item.hidden_trait_match && (
            <div className="mb-3 p-3 bg-purple-50 rounded-lg">
              <p className="text-sm text-purple-700 font-medium">
                🎯 Hidden Trait: {item.hidden_trait_match}
              </p>
            </div>
          )}
          
          {item.why_secret && (
            <div className="mb-4 p-3 bg-amber-50 rounded-lg border-l-4 border-amber-400">
              <p className="text-sm text-amber-800">
                💡 {item.why_secret}
              </p>
            </div>
          )}
          
          <div className="space-y-2 mb-4 text-sm text-gray-600">
            {item.address && (
              <div className="flex items-start gap-2">
                <span className="text-gray-400">📍</span>
                <span>{item.address}</span>
              </div>
            )}
            {item.phone && (
              <div className="flex items-center gap-2">
                <span className="text-gray-400">📞</span>
                <a href={`tel:${item.phone}`} className="text-purple-600 hover:text-purple-700">
                  {item.phone}
                </a>
              </div>
            )}
            {item.price_range && (
              <div className="flex items-center gap-2">
                <span className="text-gray-400">💰</span>
                <span>{item.price_range}</span>
              </div>
            )}
            {item.best_time_to_visit && (
              <div className="flex items-center gap-2">
                <span className="text-gray-400">🕐</span>
                <span>{item.best_time_to_visit}</span>
              </div>
            )}
            {item.location && (
              <div className="flex items-center gap-2">
                <span className="text-gray-400">🗺️</span>
                <span className="text-xs">
                  {item.location.address || `${item.location.latitude}, ${item.location.longitude}`}
                </span>
              </div>
            )}
          </div>
          
          {item.url && (
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center text-purple-600 hover:text-purple-700 font-semibold transition-colors"
            >
              Discover Secret →
              <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </a>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-amber-50">
      <div className="container mx-auto px-4 py-8 md:py-12">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.back()}
            className="mb-4 text-purple-600 hover:text-purple-700 font-semibold flex items-center transition-colors"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl flex items-center justify-center text-4xl">
              🔮
            </div>
            <div>
              <h1 className="text-4xl font-bold text-purple-900 mb-2">
                Secret Recommendations
              </h1>
              <p className="text-purple-600">
                Hidden gems based on your personality traits
              </p>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex flex-col items-center gap-4">
              <div className="w-12 h-12 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-purple-600 font-medium">Loading secret recommendations...</p>
            </div>
          </div>
        ) : secretRecommendations.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {secretRecommendations.map((item, idx) => (
              <SecretCard key={item.id || idx} item={item} />
            ))}
          </div>
        ) : (
          <div className="text-center py-20 bg-white rounded-2xl shadow-lg">
            <div className="text-6xl mb-4">🔮</div>
            <h2 className="text-2xl font-bold text-purple-900 mb-2">
              No Secret Recommendations Yet
            </h2>
            <p className="text-gray-600 mb-6">
              Secret recommendations will appear here once you interact with regular recommendations.
            </p>
            <button
              onClick={() => router.push("/dashboard")}
              className="px-6 py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 transition-colors"
            >
              Go to Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

