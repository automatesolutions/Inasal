import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import Home from '@/app/page';

describe('HomePage', () => {
  it('renders the welcome message', () => {
    render(<Home />);
    
    expect(screen.getByText('INASAL')).toBeVisible();
    expect(screen.getByText('Discover the City of Smiles')).toBeVisible();
    expect(
      screen.getByText(/Experience Bacolod with AI-powered personalized recommendations/i)
    ).toBeVisible();
  });

  it('renders the get started button', () => {
    render(<Home />);
    
    const getStartedLink = screen.getByRole('link', { name: /get started/i });
    expect(getStartedLink).toBeVisible();
    expect(getStartedLink).toHaveAttribute('href', '/login');
  });

  it('has proper styling classes', () => {
    const { container } = render(<Home />);
    
    const main = container.querySelector('main');
    expect(main).not.toBeNull();
  });
});

