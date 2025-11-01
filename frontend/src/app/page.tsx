export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50">
      <main className="container mx-auto px-4 py-8">
        <div className="text-center">
          <h1 className="text-5xl font-bold text-amber-900 mb-4">
            Welcome to Bacolod
          </h1>
          <p className="text-xl text-amber-700 mb-8">
            Discover the City of Smiles with AI-powered recommendations
          </p>
          <div className="mt-8">
            <a
              href="/login"
              className="inline-block bg-amber-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-amber-700 transition-colors"
            >
              Get Started
            </a>
          </div>
        </div>
      </main>
    </div>
  );
}
