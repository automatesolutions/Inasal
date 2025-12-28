/**
 * Analytics and behavior tracking utilities
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Track a user interaction
 */
export async function trackInteraction(
  type: string,
  data: Record<string, any> = {}
): Promise<void> {
  try {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    if (!token) return; // Don't track if user not logged in

    await fetch(`${API_BASE_URL}/api/analytics/track`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        interaction_type: type,
        data,
      }),
    });
  } catch (error) {
    // Fail silently - don't interrupt user experience
    console.error('Error tracking interaction:', error);
  }
}

/**
 * Track attraction view
 */
export function trackAttractionView(attractionId: string, attractionName: string): void {
  trackInteraction('view_attraction', {
    attraction_id: attractionId,
    attraction_name: attractionName,
  });
}

/**
 * Track attraction detail click
 */
export function trackAttractionDetailClick(attractionId: string, attractionName: string): void {
  trackInteraction('click_detail', {
    attraction_id: attractionId,
    attraction_name: attractionName,
  });
}

/**
 * Track attraction save
 */
export function trackAttractionSave(attractionId: string, attractionName: string): void {
  trackInteraction('save_attraction', {
    attraction_id: attractionId,
    attraction_name: attractionName,
  });
}

/**
 * Track time on page
 */
export function trackTimeOnPage(page: string, seconds: number): void {
  trackInteraction('time_on_page', {
    page,
    duration_seconds: seconds,
  });
}

