"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { authApi, oauthApi } from "@/lib/api";
import PhoneInput from "@/components/PhoneInput";

// OAuth Button Component
function OAuthButton({ 
  provider, 
  color, 
  title, 
  iconPath 
}: { 
  provider: 'facebook' | 'twitter' | 'linkedin';
  color: string;
  title: string;
  iconPath: string;
}) {
  const [isConfigured, setIsConfigured] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Check if provider is configured
    oauthApi.getProviderStatus(provider)
      .then(status => setIsConfigured(status.configured))
      .catch(() => setIsConfigured(false));
  }, [provider]);

  const handleClick = async () => {
    setIsLoading(true);
    try {
      oauthApi.initiateLogin(provider);
    } catch (err) {
      setIsLoading(false);
      console.error(`Error initiating ${provider} login:`, err);
    }
  };

  // Allow clicking even if not configured - backend will show helpful error
  const isDisabled = isLoading;

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={isDisabled}
      className={`flex items-center justify-center px-4 py-2 border rounded-lg transition-colors relative ${
        isConfigured === false 
          ? 'border-yellow-400 bg-yellow-50/50 hover:bg-yellow-50 opacity-75' 
          : 'border-gray-300 hover:bg-gray-50'
      } ${isDisabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
      title={isConfigured === false ? `${title} (May not be configured - click to check)` : title}
    >
      {isLoading ? (
        <div className="w-5 h-5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
      ) : (
        <>
          <svg className="w-5 h-5" fill={color} viewBox="0 0 24 24">
            <path d={iconPath}/>
          </svg>
          {isConfigured === false && (
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-yellow-500 rounded-full border border-white"></span>
          )}
        </>
      )}
    </button>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [usePhone, setUsePhone] = useState(true); // Default to phone login
  const [email, setEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSendOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (usePhone) {
        console.log("📤 Sending OTP request (phone):", { phoneNumber, firstName, lastName });
        const result = await authApi.sendOTPPhone(phoneNumber, firstName, lastName);
        console.log("✅ OTP sent successfully:", result);
        setOtpSent(true);
      } else {
        console.log("📤 Sending OTP request (email):", { email, firstName, lastName });
        const result = await authApi.sendOTP(email, firstName, lastName);
        console.log("✅ OTP sent successfully:", result);
        setOtpSent(true);
      }
    } catch (err: any) {
      console.error("❌ Error sending OTP:", err);
      console.error("Error details:", {
        detail: err?.detail,
        status: err?.status,
        message: err?.message,
        fullError: err
      });
      const fallbackMessage =
        typeof err?.detail === "string"
          ? err.detail
          : err?.message || `Failed to send verification code. Status: ${err?.status || 'unknown'}. Please try again.`;
      setError(fallbackMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (usePhone) {
        await authApi.verifyOTPPhone(phoneNumber, otp, firstName, lastName);
      } else {
        await authApi.verifyOTP(email, otp, firstName, lastName);
      }
      // Redirect to chat on successful login
      router.push("/chat");
    } catch (err: any) {
      const fallbackMessage =
        typeof err?.detail === "string"
          ? err.detail
          : "Invalid verification code. Please try again.";
      setError(fallbackMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-amber-900 mb-2">
            Welcome Back!
          </h1>
          <p className="text-amber-600">
            Enter your phone number or email to receive a verification code
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {!otpSent ? (
          <>
            {/* OAuth Login Options */}
            <div className="mb-6">
              <div className="relative mb-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-gray-500">Or continue with</span>
                </div>
              </div>
              
              <div className="grid grid-cols-3 gap-3">
                <OAuthButton 
                  provider="facebook" 
                  color="#1877F2"
                  title="Login with Facebook"
                  iconPath="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"
                />
                
                <OAuthButton 
                  provider="twitter" 
                  color="#1DA1F2"
                  title="Login with Twitter"
                  iconPath="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"
                />
                
                <OAuthButton 
                  provider="linkedin" 
                  color="#0077B5"
                  title="Login with LinkedIn"
                  iconPath="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"
                />
              </div>
            </div>

            <div className="relative mb-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-gray-500">Or use email</span>
              </div>
            </div>

            <form onSubmit={handleSendOTP} className="space-y-4">
              {/* Toggle between phone and email */}
              <div className="flex gap-2 mb-4">
                <button
                  type="button"
                  onClick={() => setUsePhone(true)}
                  className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
                    usePhone
                      ? "bg-amber-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  Phone
                </button>
                <button
                  type="button"
                  onClick={() => setUsePhone(false)}
                  className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
                    !usePhone
                      ? "bg-amber-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  }`}
                >
                  Email
                </button>
              </div>

              {usePhone ? (
                <div>
                  <label
                    htmlFor="phone"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Phone Number (Philippines)
                  </label>
                  <PhoneInput
                    id="phone"
                    value={phoneNumber}
                    onChange={setPhoneNumber}
                    required
                    disabled={loading}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Format: +63 9XX XXX XXXX or 09XX XXX XXXX
                  </p>
                </div>
              ) : (
                <div>
                  <label
                    htmlFor="email"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Email Address
                  </label>
                  <input
                    type="email"
                    id="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={loading}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed text-gray-900"
                    placeholder="your.email@example.com"
                  />
                </div>
              )}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label
                    htmlFor="firstName"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    First Name
                  </label>
                  <input
                    type="text"
                    id="firstName"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    required
                    disabled={loading}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed text-gray-900"
                    placeholder="Juan"
                    autoComplete="given-name"
                  />
                </div>
                <div>
                  <label
                    htmlFor="lastName"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Last Name
                  </label>
                  <input
                    type="text"
                    id="lastName"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    required
                    disabled={loading}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed text-gray-900"
                    placeholder="Dela Cruz"
                    autoComplete="family-name"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-amber-600 text-white py-3 rounded-lg font-semibold hover:bg-amber-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Sending..." : "Send Verification Code"}
              </button>
            </form>
          </>
        ) : (
          <form onSubmit={handleVerifyOTP} className="space-y-4">
            <div>
              <label
                htmlFor="otp"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Verification Code
              </label>
              <input
                type="text"
                id="otp"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                required
                maxLength={6}
                disabled={loading}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent text-center text-2xl tracking-widest disabled:bg-gray-100 disabled:cursor-not-allowed text-gray-900"
                placeholder="000000"
              />
              <p className="text-sm text-gray-500 mt-2">
                We sent a code to {usePhone ? phoneNumber : email}
              </p>
              <p className="text-xs text-amber-600 mt-1">
                {usePhone ? "Check your phone for the 6-digit code" : "Check your email inbox for the 6-digit code"}
              </p>
            </div>
            <button
              type="submit"
              disabled={loading || otp.length !== 6}
              className="w-full bg-amber-600 text-white py-3 rounded-lg font-semibold hover:bg-amber-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Verifying..." : "Verify & Login"}
            </button>
            <button
              type="button"
              onClick={() => {
                setOtpSent(false);
                setOtp("");
                setError("");
                setFirstName("");
                setLastName("");
                setPhoneNumber("");
                setEmail("");
              }}
              disabled={loading}
              className="w-full text-amber-600 py-2 hover:text-amber-700 disabled:opacity-50"
            >
              Change {usePhone ? "Phone" : "Email"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

