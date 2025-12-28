/**
 * API client configuration and utilities
 * 
 * Architecture:
 * - Frontend → FastAPI (orchestration) → Strapi (content) + Make.com (AI workflows)
 * - All API calls go through FastAPI, which proxies to Strapi/Make.com as needed
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const STRAPI_URL = process.env.NEXT_PUBLIC_STRAPI_URL || 'http://localhost:1337';

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
    const errorData = await response.json().catch(() => ({}));
    const error: ApiError = {
      detail: errorData.detail || `HTTP error! status: ${response.status}`,
      status: response.status,
    };
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
  async sendOTP(email: string, firstName: string, lastName: string): Promise<{ message: string }> {
    return apiRequest('/api/auth/send-otp', {
      method: 'POST',
      body: JSON.stringify({ email, first_name: firstName, last_name: lastName }),
    });
  },

  /**
   * Verify OTP and get access token
   */
  async verifyOTP(
    email: string,
    otp: string,
    firstName: string,
    lastName: string
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
      body: JSON.stringify({ email, otp, first_name: firstName, last_name: lastName }),
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

/**
 * Recommendation API functions
 */
export interface RecommendationItem {
  name: string;
  url: string;
  description: string;
  match_score: number;
  category?: string;
  image?: string;
}

export interface SecretRecommendation extends RecommendationItem {
  hidden_trait_match?: string;
  why_secret?: string;
}

export interface RecommendationsResponse {
  hotels: RecommendationItem[];
  restaurants: RecommendationItem[];
  entertainment: RecommendationItem[];
  tourist_spots: RecommendationItem[];
  secret_recommendations: SecretRecommendation[];
}

export const recommendationApi = {
  /**
   * Get all recommendations (hotels, restaurants, entertainment, tourist spots)
   */
  async getRecommendations(): Promise<RecommendationsResponse> {
    return apiRequest<RecommendationsResponse>('/api/recommendations');
  },

  /**
   * Get secret recommendations (hidden traits)
   */
  async getSecretRecommendations(): Promise<{
    secret_recommendations: SecretRecommendation[];
  }> {
    return apiRequest(`/api/recommendations/secret`);
  },
};

/**
 * OAuth API functions
 */
export const oauthApi = {
  /**
   * Initiate OAuth login
   */
  initiateLogin(provider: 'facebook' | 'twitter' | 'linkedin'): void {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    window.location.href = `${apiUrl}/api/auth/oauth/${provider}/authorize`;
  },

  /**
   * Check OAuth provider status (public endpoint, no auth required)
   */
  async getProviderStatus(provider: 'facebook' | 'twitter' | 'linkedin'): Promise<{
    configured: boolean;
    provider: string;
  }> {
    // Status endpoint is public, no auth token needed
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${apiUrl}/api/auth/oauth/${provider}/status`);
    if (!response.ok) {
      throw new Error(`Failed to check ${provider} status`);
    }
    return response.json();
  },
};

