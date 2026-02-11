"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { chatApi } from "@/lib/api";

interface SafetyItem {
  id: string;
  name: string;
  description: string;
  type: "scam" | "danger_zone";
  area: string;
  advice: string;
  warning_signs?: string[];
  how_to_avoid?: string[];
  severity?: "low" | "medium" | "high";
  location?: {
    latitude: number;
    longitude: number;
    address: string;
  };
  links?: {
    website?: string;
    details?: string;
    official?: string;
  };
}

export default function SafetyPage() {
  const router = useRouter();
  const [safetyItems, setSafetyItems] = useState<SafetyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterType, setFilterType] = useState<"all" | "scam" | "danger_zone">("all");

  useEffect(() => {
    loadSafetyItems();
  }, []);

  const loadSafetyItems = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await chatApi.getWelcomeMessage();
      const items = response.recommendations?.places_to_avoid || [];
      setSafetyItems(items);
    } catch (err: any) {
      const errorMessage = err.detail || "Failed to load safety information";
      setError(errorMessage);
      console.error("Error loading safety items:", err);
    } finally {
      setLoading(false);
    }
  };

  const filteredItems = filterType === "all" 
    ? safetyItems 
    : safetyItems.filter(item => item.type === filterType);

  const scams = filteredItems.filter(item => item.type === "scam");
  const dangerZones = filteredItems.filter(item => item.type === "danger_zone");

  const SafetyCard = ({ item }: { item: SafetyItem }) => {
    const severityColors = {
      high: "bg-red-100 border-red-400 text-red-800",
      medium: "bg-orange-100 border-orange-400 text-orange-800",
      low: "bg-yellow-100 border-yellow-400 text-yellow-800",
    };

    const severityColor = severityColors[item.severity || "medium"];

    return (
      <div className={`bg-white rounded-xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden border-2 ${item.type === "scam" ? "border-red-200" : "border-orange-200"}`}>
        <div className="p-6">
          <div className="flex items-start justify-between mb-3">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-2xl ${item.type === "scam" ? "🔴" : "⚠️"}`}>
                  {item.type === "scam" ? "🔴" : "⚠️"}
                </span>
                <h3 className="text-xl font-bold text-gray-900">{item.name}</h3>
              </div>
              {item.severity && (
                <span className={`inline-block px-3 py-1 text-xs font-semibold rounded-full border-2 ${severityColor}`}>
                  {item.severity.toUpperCase()} SEVERITY
                </span>
              )}
            </div>
          </div>

          <p className="text-gray-700 mb-4 leading-relaxed">{item.description}</p>

          {item.area && (
            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
              <div className="flex items-start gap-2">
                <span className="text-gray-600 font-semibold">📍 Location:</span>
                <span className="text-gray-700">{item.area}</span>
              </div>
            </div>
          )}

          {item.warning_signs && item.warning_signs.length > 0 && (
            <div className="mb-4 p-3 bg-red-50 rounded-lg border-l-4 border-red-400">
              <h4 className="font-semibold text-red-900 mb-2">⚠️ Warning Signs:</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-red-800">
                {item.warning_signs.map((sign, idx) => (
                  <li key={idx}>{sign}</li>
                ))}
              </ul>
            </div>
          )}

          {item.how_to_avoid && item.how_to_avoid.length > 0 && (
            <div className="mb-4 p-3 bg-green-50 rounded-lg border-l-4 border-green-400">
              <h4 className="font-semibold text-green-900 mb-2">✅ How to Avoid:</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-green-800">
                {item.how_to_avoid.map((tip, idx) => (
                  <li key={idx}>{tip}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-4 p-3 bg-blue-50 rounded-lg border-l-4 border-blue-400">
            <p className="text-sm text-blue-900">
              <strong>💡 Safety Advice:</strong> {item.advice}
            </p>
          </div>

          {item.links && (item.links.details || item.links.official) && (
            <div className="mt-4 flex gap-2">
              {item.links.details && (
                <a
                  href={item.links.details}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors text-sm"
                >
                  View Details
                </a>
              )}
              {item.links.official && (
                <a
                  href={item.links.official}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700 transition-colors text-sm"
                >
                  Official Info
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 via-orange-50 to-yellow-50">
      <div className="container mx-auto px-4 py-8 md:py-12">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.back()}
            className="mb-4 text-gray-600 hover:text-gray-700 font-semibold flex items-center transition-colors"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 bg-gradient-to-br from-red-500 to-orange-500 rounded-2xl flex items-center justify-center text-4xl">
              ⚠️
            </div>
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">
                Scams and Danger Zones in Bacolod
              </h1>
              <p className="text-gray-600">
                Important safety information to help you stay safe during your visit
              </p>
            </div>
          </div>
        </div>

        {/* Filter Buttons */}
        <div className="mb-6 flex gap-2 flex-wrap">
          <button
            onClick={() => setFilterType("all")}
            className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
              filterType === "all"
                ? "bg-gray-800 text-white"
                : "bg-white text-gray-700 hover:bg-gray-100"
            }`}
          >
            All ({safetyItems.length})
          </button>
          <button
            onClick={() => setFilterType("scam")}
            className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
              filterType === "scam"
                ? "bg-red-600 text-white"
                : "bg-white text-red-700 hover:bg-red-50"
            }`}
          >
            Scams ({safetyItems.filter(i => i.type === "scam").length})
          </button>
          <button
            onClick={() => setFilterType("danger_zone")}
            className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
              filterType === "danger_zone"
                ? "bg-orange-600 text-white"
                : "bg-white text-orange-700 hover:bg-orange-50"
            }`}
          >
            Danger Zones ({safetyItems.filter(i => i.type === "danger_zone").length})
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex flex-col items-center gap-4">
              <div className="w-12 h-12 border-4 border-red-600 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-gray-600 font-medium">Loading safety information...</p>
            </div>
          </div>
        ) : filteredItems.length > 0 ? (
          <div className="space-y-6">
            {scams.length > 0 && (
              <div>
                <h2 className="text-2xl font-bold text-red-900 mb-4 flex items-center gap-2">
                  🔴 Scams to Watch Out For
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {scams.map((item) => (
                    <SafetyCard key={item.id} item={item} />
                  ))}
                </div>
              </div>
            )}

            {dangerZones.length > 0 && (
              <div>
                <h2 className="text-2xl font-bold text-orange-900 mb-4 flex items-center gap-2">
                  ⚠️ Dangerous Areas
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {dangerZones.map((item) => (
                    <SafetyCard key={item.id} item={item} />
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-20 bg-white rounded-2xl shadow-lg">
            <div className="text-6xl mb-4">⚠️</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              No Safety Information Available
            </h2>
            <p className="text-gray-600 mb-6">
              Safety information will be displayed here once available.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
