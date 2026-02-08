/**
 * API client configuration and utilities
 * 
 * Architecture:
 * - Frontend → FastAPI (orchestration) → Make.com (AI workflows)
 * - All API calls go through FastAPI
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
  if (token && token.trim() && token !== 'null' && token !== 'undefined') {
    defaultHeaders['Authorization'] = `Bearer ${token}`;
  }

  console.log(`🌐 API Request: ${options.method || 'GET'} ${url}`);
  if (options.body) {
    console.log(`📦 Request body:`, options.body);
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  console.log(`📥 API Response: ${response.status} ${response.statusText}`);

  if (!response.ok) {
    let errorData: any = {};
    try {
      const text = await response.text();
      console.error(`❌ Error response body:`, text);
      if (text && text.trim()) {
        errorData = JSON.parse(text);
      }
    } catch (e) {
      console.error(`❌ Could not parse error response:`, e);
    }
    
    // If it's an authentication error, clear invalid token
    if (response.status === 401 || response.status === 403) {
      if (typeof window !== 'undefined') {
        console.warn("Authentication failed, clearing token");
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_id');
        localStorage.removeItem('user_email');
        localStorage.removeItem('user_phone');
      }
    }
    
    // Extract detailed error message
    let errorMessage = `HTTP error! status: ${response.status}`;
    
    // Handle FastAPI validation errors (422)
    if (response.status === 422 && Array.isArray(errorData.detail)) {
      // Extract field-specific validation errors
      const validationErrors = errorData.detail.map((err: any) => {
        const field = err.loc?.join('.') || 'field';
        const msg = err.msg || 'Invalid value';
        return `${field}: ${msg}`;
      });
      errorMessage = validationErrors.join('. ') || errorData.detail;
    } else if (errorData.detail) {
      // Use detail if it's a string or single message
      if (typeof errorData.detail === 'string') {
        errorMessage = errorData.detail;
      } else if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
        // If it's an array, extract the first error message
        const firstError = errorData.detail[0];
        if (typeof firstError === 'string') {
          errorMessage = firstError;
        } else if (firstError.msg) {
          errorMessage = firstError.msg;
        }
      }
    }
    
    const error: ApiError = {
      detail: errorMessage,
      status: response.status,
    };
    console.error(`❌ API Error:`, error);
    throw error;
  }

  const data = await response.json();
  console.log(`✅ API Success:`, data);
  return data;
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
   * Send OTP to user's phone number
   */
  async sendOTPPhone(phoneNumber: string, firstName: string, lastName: string): Promise<{ message: string; phone_number: string }> {
    return apiRequest('/api/auth/send-otp-phone', {
      method: 'POST',
      body: JSON.stringify({ phone_number: phoneNumber, first_name: firstName, last_name: lastName }),
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

  /**
   * Verify OTP for phone number and get access token
   */
  async verifyOTPPhone(
    phoneNumber: string,
    otp: string,
    firstName: string,
    lastName: string
  ): Promise<{
    access_token: string;
    token_type: string;
    user_id: string;
    email: string;
    phone_number: string;
    personality_analysis_status: string;
  }> {
    const response = await apiRequest<{
      access_token: string;
      token_type: string;
      user_id: string;
      email: string;
      phone_number: string;
      personality_analysis_status: string;
    }>('/api/auth/verify-otp-phone', {
      method: 'POST',
      body: JSON.stringify({ phone_number: phoneNumber, otp, first_name: firstName, last_name: lastName }),
    });

    // Store token in localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', response.access_token);
      localStorage.setItem('user_id', response.user_id);
      localStorage.setItem('user_email', response.email);
      if (response.phone_number) {
        localStorage.setItem('user_phone', response.phone_number);
      }
    }

    return response;
  },
};

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') return false;
  const token = localStorage.getItem('auth_token');
  // Check if token exists and is not empty
  return !!(token && token.trim() && token !== 'null' && token !== 'undefined');
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

export interface LocationComponent {
  address: string;
  latitude: number;
  longitude: number;
}

export interface SecretRecommendation extends RecommendationItem {
  id?: number;
  hidden_trait_match?: string;
  why_secret?: string;
  expires_at?: string;
  location?: LocationComponent;
  tags?: string[];
  price_range?: string;
  rating?: number;
  phone?: string;
  address?: string;
  best_time_to_visit?: string;
  featured?: boolean;
  priority?: number;
  additional_info?: Record<string, any>;
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
};

/**
 * Chat API functions
 */
export interface WelcomeMessageResponse {
  type: string;
  content: string;
  personality_summary: string;
  recommendations: {
    hotels: any[];
    restaurants: any[];
    accommodations: any[];
    tourist_spots: any[];
    beaches: any[];
    mountains: any[];
    resorts: any[];
    places_to_avoid: any[];
    businesses: any[];
    events: any[];
    secret_spots: any[];
  };
}

export const chatApi = {
  /**
   * Get welcome message with recommendations
   */
  async getWelcomeMessage(): Promise<WelcomeMessageResponse> {
    return apiRequest<WelcomeMessageResponse>('/api/chat/welcome');
  },

  /**
   * Send chat message to MOGI
   */
  async sendMessage(message: string): Promise<{ response: string }> {
    return apiRequest<{ response: string }>('/api/chat/', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  },
};

/**
 * Secret Recommendations API functions (separate collection)
 */
export interface SecretRecommendationResponse {
  data: SecretRecommendation[];
  count: number;
}

export const secretRecommendationsApi = {
  /**
   * Get all secret recommendations for the current user
   */
  async getSecretRecommendations(limit: number = 50): Promise<SecretRecommendationResponse> {
    return apiRequest<SecretRecommendationResponse>(`/api/secret-recommendations?limit=${limit}`);
  },

  /**
   * Get a single secret recommendation by ID
   */
  async getSecretRecommendation(id: number): Promise<{ data: SecretRecommendation }> {
    return apiRequest<{ data: SecretRecommendation }>(`/api/secret-recommendations/${id}`);
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

