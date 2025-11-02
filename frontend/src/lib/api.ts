/**
 * API client configuration and utilities
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ApiError {
  detail: string;
  status?: number;
}

/**
 * Make an API request with error handling
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
  };

  // Add auth token if available
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  if (token) {
    defaultHeaders['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({
      detail: `HTTP error! status: ${response.status}`,
      status: response.status,
    }));
    throw error;
  }

  return response.json();
}

/**
 * Auth API functions
 */
export const authApi = {
  /**
   * Send OTP to user's email
   */
  async sendOTP(email: string): Promise<{ message: string }> {
    return apiRequest('/api/auth/send-otp', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  },

  /**
   * Verify OTP and get access token
   */
  async verifyOTP(
    email: string,
    otp: string
  ): Promise<{
    access_token: string;
    token_type: string;
    user_id: string;
    email: string;
  }> {
    const response = await apiRequest<{
      access_token: string;
      token_type: string;
      user_id: string;
      email: string;
    }>('/api/auth/verify-otp', {
      method: 'POST',
      body: JSON.stringify({ email, otp }),
    });

    // Store token in localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', response.access_token);
      localStorage.setItem('user_id', response.user_id);
      localStorage.setItem('user_email', response.email);
    }

    return response;
  },
};

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') return false;
  return !!localStorage.getItem('auth_token');
}

/**
 * Get auth token
 */
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth_token');
}

/**
 * Logout user
 */
export function logout(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('auth_token');
  localStorage.removeItem('user_id');
  localStorage.removeItem('user_email');
}

