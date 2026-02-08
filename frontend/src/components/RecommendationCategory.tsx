"use client";

import { useState } from "react";
import { RecommendationCard } from "./RecommendationCard";

interface RecommendationCategoryProps {
  title: string;
  icon: string;
  items: any[];
  isHiddenGem?: boolean;
  isSecretSpot?: boolean;
}

export function RecommendationCategory({ title, icon, items, isHiddenGem = false, isSecretSpot = false }: RecommendationCategoryProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!items || items.length === 0) {
    return null;
  }

  return (
    <div className="mb-6">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 bg-amber-50 rounded-lg hover:bg-amber-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-2xl">{icon}</span>
          <h3 className="text-lg font-semibold text-amber-900">{title}</h3>
          <span className="text-sm text-amber-600">({items.length})</span>
        </div>
        <svg
          className={`w-5 h-5 text-amber-700 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      
      {isExpanded && (
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item, idx) => (
            <RecommendationCard
              key={item.id || idx}
              recommendation={item}
              isHiddenGem={isHiddenGem}
              isSecretSpot={isSecretSpot}
            />
          ))}
        </div>
      )}
    </div>
  );
}
