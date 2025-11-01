"use client";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-amber-900 mb-8">
          Your Personalized Bacolod Experience
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Recommended Destinations */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-semibold text-amber-900 mb-4">
              Recommended for You
            </h2>
            <p className="text-gray-600">
              AI-curated destinations based on your personality profile
            </p>
          </div>

          {/* Hidden Gems */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-semibold text-amber-900 mb-4">
              Hidden Gems
            </h2>
            <p className="text-gray-600">
              Discover local favorites off the beaten path
            </p>
          </div>

          {/* Cultural Highlights */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-semibold text-amber-900 mb-4">
              Cultural Highlights
            </h2>
            <p className="text-gray-600">
              Experience the rich culture of Bacolod
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

