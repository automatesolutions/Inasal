import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import DashboardPage from '@/app/dashboard/page';

describe('DashboardPage', () => {
  it('renders the dashboard title', () => {
    render(<DashboardPage />);
    
    expect(
      screen.getByText('Your Personalized Bacolod Experience')
    ).toBeVisible();
  });

  it('renders recommended destinations section', () => {
    render(<DashboardPage />);
    
    expect(screen.getByText('Recommended for You')).toBeVisible();
    expect(
      screen.getByText(/AI-curated destinations based on your personality profile/i)
    ).toBeVisible();
  });

  it('renders hidden gems section', () => {
    render(<DashboardPage />);
    
    expect(screen.getByText('Hidden Gems')).toBeVisible();
    expect(
      screen.getByText(/Discover local favorites off the beaten path/i)
    ).toBeVisible();
  });

  it('renders cultural highlights section', () => {
    render(<DashboardPage />);
    
    expect(screen.getByText('Cultural Highlights')).toBeVisible();
    expect(
      screen.getByText(/Experience the rich culture of Bacolod/i)
    ).toBeVisible();
  });

  it('has proper layout structure', () => {
    const { container } = render(<DashboardPage />);
    
    // Check for grid layout
    const grid = container.querySelector('.grid');
    expect(grid).not.toBeNull();
  });
});

