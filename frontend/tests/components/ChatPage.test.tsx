import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatPage from '@/app/chat/page';

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

describe('ChatPage', () => {
  it('renders the chat interface', () => {
    render(<ChatPage />);
    
    expect(screen.getByText('Chat with Your Local Guide')).toBeVisible();
    expect(screen.getByPlaceholderText(/ask about bacolod/i)).toBeVisible();
    expect(screen.getByRole('button', { name: /send/i })).toBeVisible();
  });

  it('shows empty state message when no messages', () => {
    render(<ChatPage />);
    
    expect(screen.getByText(/ask me anything about bacolod/i)).toBeVisible();
    expect(
      screen.getByText(/I can help you discover places, plan itineraries/i)
    ).toBeVisible();
  });

  it('allows user to type a message', async () => {
    const user = userEvent.setup();
    render(<ChatPage />);
    
    const input = screen.getByPlaceholderText(/ask about bacolod/i);
    await user.type(input, 'What should I visit?');
    
    expect(input).toHaveValue('What should I visit?');
  });

  it('sends a message when form is submitted', async () => {
    const user = userEvent.setup();
    
    render(<ChatPage />);
    
    const input = screen.getByPlaceholderText(/ask about bacolod/i);
    const sendButton = screen.getByRole('button', { name: /send/i });
    
    await user.type(input, 'Tell me about Bacolod');
    await user.click(sendButton);
    
    // Input should be cleared
    expect(input).toHaveValue('');
    
    // User message should appear
    await waitFor(() => {
      expect(screen.getByText('Tell me about Bacolod')).toBeVisible();
    }, { timeout: 2000 });
  }, { timeout: 5000 });

  it('disables input and button while loading', async () => {
    const user = userEvent.setup();
    
    render(<ChatPage />);
    
    const input = screen.getByPlaceholderText(/ask about bacolod/i);
    const sendButton = screen.getByRole('button', { name: /send/i });
    
    await user.type(input, 'Test message');
    await user.click(sendButton);
    
    // Check if loading state appears (the bouncing dots) and inputs are disabled
    await waitFor(() => {
      expect(input).toBeDisabled();
      expect(sendButton).toBeDisabled();
    }, { timeout: 2000 });
  }, { timeout: 5000 });

  it('does not send empty messages', async () => {
    const user = userEvent.setup();
    render(<ChatPage />);
    
    const sendButton = screen.getByRole('button', { name: /send/i });
    await user.click(sendButton);
    
    // Should still show empty state
    expect(screen.getByText(/ask me anything about bacolod/i)).toBeInTheDocument();
  });
});

