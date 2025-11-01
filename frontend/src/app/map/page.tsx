"use client";

export default function MapPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-amber-900 mb-8">
          Explore Bacolod on the Map
        </h1>

        <div className="bg-white rounded-lg shadow-lg p-6 h-[600px]">
          <div className="h-full flex items-center justify-center border-2 border-dashed border-gray-300 rounded-lg">
            <div className="text-center">
              <p className="text-gray-600 mb-4">Google Maps integration coming soon</p>
              <p className="text-sm text-gray-500">
                Interactive map with AI-curated pins for destinations, food spots, and events
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

