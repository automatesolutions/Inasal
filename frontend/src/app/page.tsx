"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated, logout } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    setIsLoaded(true);
    // Always show landing page - users must click "Get Started" to login
    // No auto-redirect to chat
    // If there's an invalid token, clear it
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('auth_token');
      if (token && (token === 'null' || token === 'undefined' || !token.trim())) {
        logout(); // Clear invalid token
      }
    }
  }, []);

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Background Image - Optimized with smooth blending */}
      <div 
        className="absolute inset-0 transition-transform duration-[20s] ease-out"
        style={{
          backgroundImage: 'url(/BcolodinsalFI.jpg)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
          imageRendering: 'auto',
          WebkitBackfaceVisibility: 'hidden',
          backfaceVisibility: 'hidden',
          transform: 'translateZ(0) scale(1.05)',
        }}
      >
        {/* Smooth gradient overlays for seamless blending */}
        {/* Main warm overlay - smooth transition */}
        <div className="absolute inset-0 bg-gradient-to-br from-amber-950/75 via-orange-900/60 to-amber-950/75 transition-opacity duration-1000"></div>
        
        {/* Top gradient - smooth fade for text area */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-black/20 via-black/5 to-transparent"></div>
        
        {/* Bottom gradient - smooth fade for logo area */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent via-black/10 to-black/30"></div>
        
        {/* Vignette effect for smooth edges */}
        <div className="absolute inset-0 bg-radial-gradient from-transparent via-transparent to-black/20"
          style={{
            background: 'radial-gradient(ellipse at center, transparent 0%, transparent 40%, rgba(0,0,0,0.15) 100%)',
          }}
        ></div>
        
        {/* Side gradients for smooth blending */}
        <div className="absolute inset-0 bg-gradient-to-r from-amber-950/30 via-transparent to-amber-950/30"></div>
      </div>

      {/* Enhanced decorative background overlays */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Subtle sugar cane silhouette pattern */}
        <div className="absolute bottom-0 left-0 right-0 h-1/3 opacity-30">
          <svg className="w-full h-full" viewBox="0 0 1200 400" preserveAspectRatio="none">
            <path 
              d="M0,400 Q200,350 400,380 T800,370 T1200,400" 
              fill="rgba(34, 139, 34, 0.15)" 
            />
            <path 
              d="M0,400 Q150,330 300,360 T600,350 T900,365 T1200,400" 
              fill="rgba(46, 125, 50, 0.2)" 
            />
          </svg>
        </div>

        {/* Enhanced Masskara-inspired colorful decorations with animation */}
        <div className="absolute top-20 left-10 w-24 h-24 bg-yellow-400/20 rounded-full blur-2xl animate-pulse"></div>
        <div className="absolute top-40 right-20 w-40 h-40 bg-orange-400/20 rounded-full blur-2xl animate-pulse" style={{ animationDelay: '1s' }}></div>
        <div className="absolute bottom-40 left-1/4 w-32 h-32 bg-amber-400/20 rounded-full blur-2xl animate-pulse" style={{ animationDelay: '2s' }}></div>
        <div className="absolute top-1/3 right-1/3 w-20 h-20 bg-red-400/20 rounded-full blur-2xl animate-pulse" style={{ animationDelay: '0.5s' }}></div>
      </div>

      <main className="container mx-auto px-4 py-12 md:py-20 relative z-10 min-h-screen flex items-center justify-center">
        <div className="text-center max-w-4xl mx-auto">
          {/* Main Title - INASAL with enhanced styling */}
          <div className={`mb-8 transition-all duration-1000 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}>
            <h1 className="text-6xl sm:text-7xl md:text-8xl lg:text-9xl font-black mb-4 tracking-tight">
              <span className="bg-gradient-to-r from-white via-amber-50 to-white bg-clip-text text-transparent drop-shadow-[0_0_30px_rgba(251,191,36,0.5)]">
                INASAL
              </span>
            </h1>
            
            {/* Enhanced decorative divider */}
            <div className="flex items-center justify-center gap-3 mt-4">
              <div className="h-1 w-16 bg-gradient-to-r from-transparent via-amber-400 to-amber-500 rounded-full"></div>
              <div className="h-2 w-3 bg-amber-400 rounded-full shadow-lg shadow-amber-400/50"></div>
              <div className="h-1 w-16 bg-gradient-to-l from-transparent via-orange-400 to-orange-500 rounded-full"></div>
            </div>
            
            {/* Subtitle location */}
            <p className="text-sm md:text-base text-amber-200/80 mt-4 tracking-wider uppercase font-semibold letter-spacing-wider">
              Bacolod · Philippines
            </p>
          </div>
          
          {/* Main tagline with better spacing */}
          <div className={`mb-6 transition-all duration-1000 delay-200 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}>
            <p className="text-2xl sm:text-3xl md:text-4xl text-white mb-4 font-bold drop-shadow-[0_2px_10px_rgba(0,0,0,0.5)]">
              Discover the REAL City of Smiles
            </p>
            <p className="text-base sm:text-lg md:text-xl text-amber-50/90 max-w-2xl mx-auto leading-relaxed drop-shadow-md">
              Uncover <strong>secret local gems</strong>, discover businesses and events, plus essential safety tips to <strong>avoid scams and danger</strong>
            </p>
          </div>
          
          {/* Enhanced CTA Button */}
          <div className={`mb-12 transition-all duration-1000 delay-400 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}>
            <a
              href="/login"
              className="group relative inline-block"
            >
              {/* Glow effect */}
              <div className="absolute -inset-1 bg-gradient-to-r from-amber-500 via-orange-500 to-amber-500 rounded-2xl blur-lg opacity-60 group-hover:opacity-100 transition-opacity duration-300"></div>
              
              {/* Button */}
              <div className="relative bg-gradient-to-r from-amber-600 via-orange-500 to-amber-600 text-white px-12 py-5 rounded-2xl font-bold text-lg md:text-xl shadow-2xl group-hover:shadow-amber-500/50 transition-all duration-300 transform group-hover:scale-105">
                <span className="relative z-10 flex items-center gap-2">
                  Get Started
                  <svg className="w-5 h-5 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </span>
              </div>
            </a>
          </div>

          {/* Enhanced decorative elements with hover effects */}
          <div className={`transition-all duration-1000 delay-500 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}>
            <div className="flex flex-wrap justify-center gap-6 md:gap-8 lg:gap-10">
              {[
                { icon: '🎭', label: 'Culture' },
                { icon: '🍗', label: 'Food' },
                { icon: '🌴', label: 'Nature' },
                { icon: '🏛️', label: 'History' },
                { icon: '🎪', label: 'Events' },
              ].map((item, index) => (
                <div
                  key={index}
                  className="flex flex-col items-center gap-2 group cursor-pointer transform transition-all duration-300 hover:scale-125"
                >
                  <div className="text-4xl md:text-5xl drop-shadow-lg filter group-hover:brightness-125 transition-all duration-300">
                    {item.icon}
                  </div>
                  <span className="text-xs text-white/60 font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    {item.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* Company Logo - Bottom Left - Smoothly Blended */}
      <div className={`fixed bottom-6 left-12 md:left-16 z-50 transition-all duration-1000 delay-700 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}>
        <div className="relative group">
          {/* Smooth gradient backdrop that blends with background */}
          <div 
            className="absolute -inset-3 rounded-2xl opacity-80 backdrop-blur-lg transition-all duration-300 group-hover:opacity-100"
            style={{
              background: 'linear-gradient(135deg, rgba(180, 83, 9, 0.3) 0%, rgba(154, 52, 18, 0.4) 50%, rgba(120, 53, 15, 0.3) 100%)',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
            }}
          ></div>
          
          {/* Subtle border that matches the theme */}
          <div className="absolute -inset-2 rounded-2xl border border-amber-500/20 opacity-50 group-hover:opacity-80 transition-opacity duration-300"></div>
          
          {/* Logo container with smooth padding */}
          <div className="relative p-3">
            <img
              src="/Company_Logo.png"
              alt="Company Logo"
              className="h-14 md:h-20 w-auto transition-all duration-300 transform group-hover:scale-110"
              style={{
                filter: 'drop-shadow(0 3px 8px rgba(0,0,0,0.7)) brightness(1.25) contrast(1.2)',
              }}
            />
          </div>
          
          {/* Subtle glow on hover */}
          <div className="absolute -inset-2 rounded-2xl bg-gradient-to-br from-amber-400/0 via-orange-400/0 to-amber-400/0 group-hover:from-amber-400/20 group-hover:via-orange-400/10 group-hover:to-amber-400/20 transition-all duration-300 blur-md"></div>
        </div>
      </div>
    </div>
  );
}
