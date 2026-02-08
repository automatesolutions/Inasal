"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import PhoneInput from "@/components/PhoneInput";

export default function LoginPage() {
  const router = useRouter();
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
      console.log("📤 Sending OTP request (phone):", { phoneNumber, firstName, lastName });
      const result = await authApi.sendOTPPhone(phoneNumber, firstName, lastName);
      console.log("✅ OTP sent successfully:", result);
      setOtpSent(true);
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
      await authApi.verifyOTPPhone(phoneNumber, otp, firstName, lastName);
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
            Enter your phone number to receive a verification code
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {!otpSent ? (
          <form onSubmit={handleSendOTP} className="space-y-4">
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
                We sent a code to {phoneNumber}
              </p>
              <p className="text-xs text-amber-600 mt-1">
                Check your phone for the 6-digit code
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
              }}
              disabled={loading}
              className="w-full text-amber-600 py-2 hover:text-amber-700 disabled:opacity-50"
            >
              Change Phone Number
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

