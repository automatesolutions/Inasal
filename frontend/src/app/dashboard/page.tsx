"use client";

import { useState, useEffect } from "react";
import { recommendationApi, type RecommendationItem, type SecretRecommendation } from "@/lib/api";

type SectionType = "hotels" | "restaurants" | "entertainment" | "tourist_spots" | "secret" | null;

export default function DashboardPage() {
  const [activeSection, setActiveSection] = useState<SectionType>(null);
  const [hotels, setHotels] = useState<RecommendationItem[]>([]);
  const [restaurants, setRestaurants] = useState<RecommendationItem[]>([]);
  const [entertainment, setEntertainment] = useState<RecommendationItem[]>([]);
  const [touristSpots, setTouristSpots] = useState<RecommendationItem[]>([]);
  const [secretRecommendations, setSecretRecommendations] = useState<SecretRecommendation[]>([]);
  const [loading, setLoading] = useState<{ [key: string]: boolean }>({});
  const [error, setError] = useState<string>("");
  const [secretUnlocked, setSecretUnlocked] = useState(false);

  // Auto-load recommendations on mount
  useEffect(() => {
    const initializeRecommendations = async () => {
      await loadRecommendations();
      setActiveSection("hotels"); // Auto-expand hotels section
    };
    
    initializeRecommendations();
  }, []);

  const loadRecommendations = async () => {
    setLoading((prev) => ({ ...prev, all: true }));
    setError("");
    try {
      const response = await recommendationApi.getRecommendations();
      setHotels(response.hotels || []);
      setRestaurants(response.restaurants || []);
      setEntertainment(response.entertainment || []);
      setTouristSpots(response.tourist_spots || []);
      setSecretRecommendations(response.secret_recommendations || []);
    } catch (err: any) {
      const errorMessage = err.detail || "Failed to load recommendations";
      setError(errorMessage);
      console.error("Error loading recommendations:", err);
    } finally {
      setLoading((prev) => ({ ...prev, all: false }));
    }
  };

  const handleSectionClick = (section: SectionType) => {
    setActiveSection(activeSection === section ? null : section);
  };

  const handleRecommendationClick = (item: RecommendationItem) => {
    // Track clicks to unlock secret page
    if (!secretUnlocked && (item.match_score > 0.8 || Math.random() > 0.7)) {
      setSecretUnlocked(true);
    }
    // Open URL in new tab
    if (item.url) {
      window.open(item.url, '_blank', 'noopener,noreferrer');
    }
  };

  const RecommendationCard = ({ item }: { item: RecommendationItem }) => {
    return (
      <div 
        className="bg-white rounded-xl shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden group border border-gray-100 cursor-pointer"
        onClick={() => handleRecommendationClick(item)}
      >
        {item.image && (
          <div className="w-full h-48 overflow-hidden bg-gray-200">
            <img
              src={item.image}
              alt={item.name}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
              onError={(e) => {
                // Hide image if it fails to load
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </div>
        )}
        <div className="p-5">
          <div className="flex items-start justify-between mb-3">
            <div className="flex-1">
              <h3 className="text-lg font-bold text-amber-900 mb-1 group-hover:text-amber-700 transition-colors">
                {item.name}
              </h3>
              {item.category && (
                <span className="inline-block px-3 py-1 text-xs font-semibold text-amber-700 bg-amber-100 rounded-full">
                  {item.category}
                </span>
              )}
            </div>
            <div className="ml-3 text-right">
              <div className="text-xs text-gray-500 mb-1">Match</div>
              <div className="text-sm font-bold text-amber-600">
                {Math.round(item.match_score * 100)}%
              </div>
            </div>
          </div>
          
          <p className="text-sm text-gray-600 mb-4 line-clamp-3">
            {item.description}
          </p>
          
          {item.url && (
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center text-sm font-semibold text-amber-600 hover:text-amber-700 transition-colors"
            >
              Visit Website →
            </a>
          )}
        </div>
      </div>
    );
  };

  const SecretCard = ({ item }: { item: SecretRecommendation }) => {
    return (
      <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden border-2 border-purple-200">
        <div className="p-5">
          <div className="flex items-start justify-between mb-3">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">🔮</span>
                <h3 className="text-lg font-bold text-purple-900">
                  {item.name}
                </h3>
              </div>
              {item.hidden_trait_match && (
                <span className="inline-block px-3 py-1 text-xs font-semibold text-purple-700 bg-purple-100 rounded-full">
                  {item.hidden_trait_match}
                </span>
              )}
            </div>
            <div className="ml-3 text-right">
              <div className="text-xs text-purple-500 mb-1">Match</div>
              <div className="text-sm font-bold text-purple-600">
                {Math.round(item.match_score * 100)}%
              </div>
            </div>
          </div>
          
          <p className="text-sm text-gray-700 mb-3">
            {item.description}
          </p>
          
          {item.why_secret && (
            <div className="mb-3 p-2 bg-purple-100 rounded-md">
              <p className="text-xs text-purple-800 italic">
                💡 {item.why_secret}
              </p>
            </div>
          )}
          
          {item.url && (
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center text-sm font-semibold text-purple-600 hover:text-purple-700 transition-colors"
            >
              Discover Secret →
            </a>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50">
      <div className="container mx-auto px-4 py-8 md:py-12">
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="text-4xl md:text-5xl font-bold text-amber-900 mb-3">
            Your Personalized Bacolod Experience
          </h1>
          <p className="text-lg text-amber-700 max-w-2xl mx-auto">
            Discover amazing places tailored to your personality
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {/* Main Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {/* Hotels */}
          <div
            className={`bg-white rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden cursor-pointer border-2 ${
              activeSection === "hotels"
                ? "border-amber-500 shadow-2xl scale-[1.02]"
                : "border-transparent hover:border-amber-200"
            }`}
            onClick={() => handleSectionClick("hotels")}
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center text-2xl">
                  🏨
                </div>
                {activeSection === "hotels" ? (
                  <span className="text-amber-600 font-semibold">▼</span>
                ) : (
                  <span className="text-gray-400">▶</span>
                )}
              </div>
              <h2 className="text-2xl font-bold text-amber-900 mb-3">Hotels</h2>
              <p className="text-gray-600 mb-2">
                {hotels.length} recommendations
              </p>
              {loading.all && (
                <div className="flex items-center gap-2 text-amber-600 text-sm">
                  <div className="w-4 h-4 border-2 border-amber-600 border-t-transparent rounded-full animate-spin"></div>
                  Loading...
                </div>
              )}
            </div>
          </div>

          {/* Restaurants */}
          <div
            className={`bg-white rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden cursor-pointer border-2 ${
              activeSection === "restaurants"
                ? "border-amber-500 shadow-2xl scale-[1.02]"
                : "border-transparent hover:border-amber-200"
            }`}
            onClick={() => handleSectionClick("restaurants")}
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-pink-500 rounded-xl flex items-center justify-center text-2xl">
                  🍽️
                </div>
                {activeSection === "restaurants" ? (
                  <span className="text-amber-600 font-semibold">▼</span>
                ) : (
                  <span className="text-gray-400">▶</span>
                )}
              </div>
              <h2 className="text-2xl font-bold text-amber-900 mb-3">Restaurants</h2>
              <p className="text-gray-600 mb-2">
                {restaurants.length} recommendations
              </p>
              {loading.all && (
                <div className="flex items-center gap-2 text-amber-600 text-sm">
                  <div className="w-4 h-4 border-2 border-amber-600 border-t-transparent rounded-full animate-spin"></div>
                  Loading...
                </div>
              )}
            </div>
          </div>

          {/* Entertainment */}
          <div
            className={`bg-white rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden cursor-pointer border-2 ${
              activeSection === "entertainment"
                ? "border-amber-500 shadow-2xl scale-[1.02]"
                : "border-transparent hover:border-amber-200"
            }`}
            onClick={() => handleSectionClick("entertainment")}
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-indigo-500 rounded-xl flex items-center justify-center text-2xl">
                  🎭
                </div>
                {activeSection === "entertainment" ? (
                  <span className="text-amber-600 font-semibold">▼</span>
                ) : (
                  <span className="text-gray-400">▶</span>
                )}
              </div>
              <h2 className="text-2xl font-bold text-amber-900 mb-3">Entertainment</h2>
              <p className="text-gray-600 mb-2">
                {entertainment.length} recommendations
              </p>
              {loading.all && (
                <div className="flex items-center gap-2 text-amber-600 text-sm">
                  <div className="w-4 h-4 border-2 border-amber-600 border-t-transparent rounded-full animate-spin"></div>
                  Loading...
                </div>
              )}
            </div>
          </div>

          {/* Tourist Spots */}
          <div
            className={`bg-white rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden cursor-pointer border-2 ${
              activeSection === "tourist_spots"
                ? "border-amber-500 shadow-2xl scale-[1.02]"
                : "border-transparent hover:border-amber-200"
            }`}
            onClick={() => handleSectionClick("tourist_spots")}
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-emerald-500 rounded-xl flex items-center justify-center text-2xl">
                  🗺️
                </div>
                {activeSection === "tourist_spots" ? (
                  <span className="text-amber-600 font-semibold">▼</span>
                ) : (
                  <span className="text-gray-400">▶</span>
                )}
              </div>
              <h2 className="text-2xl font-bold text-amber-900 mb-3">Tourist Spots</h2>
              <p className="text-gray-600 mb-2">
                {touristSpots.length} recommendations
              </p>
              {loading.all && (
                <div className="flex items-center gap-2 text-amber-600 text-sm">
                  <div className="w-4 h-4 border-2 border-amber-600 border-t-transparent rounded-full animate-spin"></div>
                  Loading...
                </div>
              )}
            </div>
          </div>

          {/* Secret Page */}
          <div
            className={`bg-gradient-to-br from-purple-100 to-pink-100 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden cursor-pointer border-2 ${
              activeSection === "secret"
                ? "border-purple-500 shadow-2xl scale-[1.02]"
                : secretUnlocked
                ? "border-purple-300 hover:border-purple-400"
                : "border-transparent opacity-50"
            }`}
            onClick={() => secretUnlocked && handleSectionClick("secret")}
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center text-2xl">
                  🔮
                </div>
                {activeSection === "secret" ? (
                  <span className="text-purple-600 font-semibold">▼</span>
                ) : (
                  <span className="text-gray-400">▶</span>
                )}
              </div>
              <h2 className="text-2xl font-bold text-purple-900 mb-3">Secret</h2>
              <p className="text-gray-600 mb-2">
                {secretUnlocked ? `${secretRecommendations.length} hidden gems` : "Click recommendations to unlock"}
              </p>
            </div>
          </div>
        </div>

        {/* Expanded Content Sections */}
        {activeSection === "hotels" && (
          <div className="mt-8 animate-fadeIn">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-bold text-amber-900">Hotels</h2>
              <button
                onClick={() => setActiveSection(null)}
                className="text-gray-500 hover:text-amber-600 transition-colors"
              >
                ✕ Close
              </button>
            </div>
            {hotels.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {hotels.map((item, idx) => (
                  <RecommendationCard key={idx} item={item} />
                ))}
              </div>
            ) : !loading.all ? (
              <div className="text-center py-12 bg-white rounded-xl">
                <p className="text-gray-500">No hotel recommendations available yet.</p>
              </div>
            ) : null}
          </div>
        )}

        {activeSection === "restaurants" && (
          <div className="mt-8 animate-fadeIn">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-bold text-amber-900">Restaurants</h2>
              <button
                onClick={() => setActiveSection(null)}
                className="text-gray-500 hover:text-amber-600 transition-colors"
              >
                ✕ Close
              </button>
            </div>
            {restaurants.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {restaurants.map((item, idx) => (
                  <RecommendationCard key={idx} item={item} />
                ))}
              </div>
            ) : !loading.all ? (
              <div className="text-center py-12 bg-white rounded-xl">
                <p className="text-gray-500">No restaurant recommendations available yet.</p>
              </div>
            ) : null}
          </div>
        )}

        {activeSection === "entertainment" && (
          <div className="mt-8 animate-fadeIn">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-bold text-amber-900">Entertainment</h2>
              <button
                onClick={() => setActiveSection(null)}
                className="text-gray-500 hover:text-amber-600 transition-colors"
              >
                ✕ Close
              </button>
            </div>
            {entertainment.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {entertainment.map((item, idx) => (
                  <RecommendationCard key={idx} item={item} />
                ))}
              </div>
            ) : !loading.all ? (
              <div className="text-center py-12 bg-white rounded-xl">
                <p className="text-gray-500">No entertainment recommendations available yet.</p>
              </div>
            ) : null}
          </div>
        )}

        {activeSection === "tourist_spots" && (
          <div className="mt-8 animate-fadeIn">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-bold text-amber-900">Tourist Spots</h2>
              <button
                onClick={() => setActiveSection(null)}
                className="text-gray-500 hover:text-amber-600 transition-colors"
              >
                ✕ Close
              </button>
            </div>
            {touristSpots.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {touristSpots.map((item, idx) => (
                  <RecommendationCard key={idx} item={item} />
                ))}
              </div>
            ) : !loading.all ? (
              <div className="text-center py-12 bg-white rounded-xl">
                <p className="text-gray-500">No tourist spot recommendations available yet.</p>
              </div>
            ) : null}
          </div>
        )}

        {activeSection === "secret" && secretUnlocked && (
          <div className="mt-8 animate-fadeIn">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-bold text-purple-900">🔮 Secret Recommendations</h2>
              <button
                onClick={() => setActiveSection(null)}
                className="text-gray-500 hover:text-purple-600 transition-colors"
              >
                ✕ Close
              </button>
            </div>
            <p className="text-gray-600 mb-6">
              Based on your hidden personality traits, here are some unusual recommendations you wouldn't ask for but would love:
            </p>
            {secretRecommendations.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {secretRecommendations.map((item, idx) => (
                  <SecretCard key={idx} item={item} />
                ))}
              </div>
            ) : (
              <div className="text-center py-12 bg-white rounded-xl">
                <p className="text-gray-500">No secret recommendations available yet.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
