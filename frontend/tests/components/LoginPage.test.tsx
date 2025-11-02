import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LoginPage from '@/app/login/page';

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

describe('LoginPage', () => {
  it('renders the login form', () => {
    render(<LoginPage />);
    
    expect(screen.getByText('Welcome Back!')).toBeVisible();
    expect(screen.getByLabelText(/email address/i)).toBeVisible();
    expect(screen.getByRole('button', { name: /send verification code/i })).toBeVisible();
  });

  it('allows user to enter email', async () => {
    const user = userEvent.setup();
    render(<LoginPage />);
    
    const emailInput = screen.getByLabelText(/email address/i);
    await user.type(emailInput, 'test@example.com');
    
    expect(emailInput).toHaveValue('test@example.com');
  });

  it('shows OTP form after submitting email', async () => {
    const user = userEvent.setup();
    render(<LoginPage />);
    
    const emailInput = screen.getByLabelText(/email address/i);
    const submitButton = screen.getByRole('button', { name: /send verification code/i });
    
    await user.type(emailInput, 'test@example.com');
    await user.click(submitButton);
    
    // Wait for the OTP form to appear
    await waitFor(() => {
      expect(screen.getByLabelText(/verification code/i)).toBeVisible();
    }, { timeout: 3000 });
    
    expect(screen.getByRole('button', { name: /verify & login/i })).toBeVisible();
  });

  it('allows user to change email after OTP is sent', async () => {
    const user = userEvent.setup();
    render(<LoginPage />);
    
    // Send OTP
    const emailInput = screen.getByLabelText(/email address/i);
    await user.type(emailInput, 'test@example.com');
    await user.click(screen.getByRole('button', { name: /send verification code/i }));
    
    // Wait for OTP form and click change email
    await waitFor(() => {
      expect(screen.getByLabelText(/verification code/i)).toBeVisible();
    }, { timeout: 3000 });
    
    const changeEmailButton = screen.getByRole('button', { name: /change email/i });
    expect(changeEmailButton).toBeVisible();
    await user.click(changeEmailButton);
    
    // Should show email form again
    await waitFor(() => {
      expect(screen.getByLabelText(/email address/i)).toBeVisible();
    }, { timeout: 3000 });
  });

  it('has required email validation', async () => {
    const user = userEvent.setup();
    render(<LoginPage />);
    
    const submitButton = screen.getByRole('button', { name: /send verification code/i });
    await user.click(submitButton);
    
    const emailInput = screen.getByLabelText(/email address/i);
    expect(emailInput).toBeRequired();
  });
});

