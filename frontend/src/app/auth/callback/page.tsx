"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authApi } from "@/lib/api";

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const handleCallback = async () => {
      const token = searchParams.get("token");
      const provider = searchParams.get("provider");

      if (token) {
        // Store token in localStorage
        localStorage.setItem("auth_token", token);
        
        // Extract user info from token (basic decode, for display only)
        try {
          const payload = JSON.parse(atob(token.split(".")[1]));
          if (payload.sub) {
            localStorage.setItem("user_id", payload.sub);
          }
          if (payload.email) {
            localStorage.setItem("user_email", payload.email);
          }
        } catch (e) {
          console.error("Error decoding token:", e);
        }

        // Redirect to dashboard
        router.push("/dashboard");
      } else {
        // No token, redirect to login with error
        router.push("/login?error=oauth_failed");
      }
    };

    handleCallback();
  }, [searchParams, router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-600 mx-auto mb-4"></div>
        <p className="text-amber-900">Completing login...</p>
      </div>
    </div>
  );
}

