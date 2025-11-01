"use client";

import { useState } from "react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState("");

  const handleSendOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Implement OTP sending
    setOtpSent(true);
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Implement OTP verification
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-yellow-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-amber-900 mb-2">
            Welcome Back!
          </h1>
          <p className="text-amber-600">
            Enter your email to receive a verification code
          </p>
        </div>

        {!otpSent ? (
          <form onSubmit={handleSendOTP} className="space-y-4">
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
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                placeholder="your.email@example.com"
              />
            </div>
            <button
              type="submit"
              className="w-full bg-amber-600 text-white py-3 rounded-lg font-semibold hover:bg-amber-700 transition-colors"
            >
              Send Verification Code
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
                onChange={(e) => setOtp(e.target.value)}
                required
                maxLength={6}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent text-center text-2xl tracking-widest"
                placeholder="000000"
              />
              <p className="text-sm text-gray-500 mt-2">
                We sent a code to {email}
              </p>
            </div>
            <button
              type="submit"
              className="w-full bg-amber-600 text-white py-3 rounded-lg font-semibold hover:bg-amber-700 transition-colors"
            >
              Verify & Login
            </button>
            <button
              type="button"
              onClick={() => setOtpSent(false)}
              className="w-full text-amber-600 py-2 hover:text-amber-700"
            >
              Change Email
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

