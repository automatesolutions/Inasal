import { test, expect } from '@playwright/test';

test.describe('Login Journey', () => {
  test('should display login page', async ({ page }) => {
    await page.goto('/login');
    
    await expect(page.getByText('Welcome Back!')).toBeVisible();
    await expect(page.getByLabel(/email address/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /send verification code/i })).toBeVisible();
  });

  test('should show OTP form after email submission', async ({ page }) => {
    await page.goto('/login');
    
    const emailInput = page.getByLabel(/email address/i);
    const submitButton = page.getByRole('button', { name: /send verification code/i });
    
    await emailInput.fill('test@example.com');
    await submitButton.click();
    
    await expect(page.getByLabel(/verification code/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /verify & login/i })).toBeVisible();
  });

  test('should allow changing email after OTP sent', async ({ page }) => {
    await page.goto('/login');
    
    // Send OTP
    await page.getByLabel(/email address/i).fill('test@example.com');
    await page.getByRole('button', { name: /send verification code/i }).click();
    
    // Click change email
    await expect(page.getByRole('button', { name: /change email/i })).toBeVisible();
    await page.getByRole('button', { name: /change email/i }).click();
    
    // Should show email form again
    await expect(page.getByLabel(/email address/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /send verification code/i })).toBeVisible();
  });

  test('should validate email format', async ({ page }) => {
    await page.goto('/login');
    
    const emailInput = page.getByLabel(/email address/i);
    await emailInput.fill('invalid-email');
    
    // Try to submit - browser should show validation error
    const submitButton = page.getByRole('button', { name: /send verification code/i });
    await submitButton.click();
    
    // Check if validation prevents submission (HTML5 validation)
    const validity = await emailInput.evaluate((el: HTMLInputElement) => el.validity.valid);
    expect(validity).toBe(false);
  });
});

test.describe('Navigation', () => {
  test('should navigate from home to login', async ({ page }) => {
    await page.goto('/');
    
    const getStartedLink = page.getByRole('link', { name: /get started/i });
    await expect(getStartedLink).toBeVisible();
    await getStartedLink.click();
    
    await expect(page).toHaveURL(/.*login/);
    await expect(page.getByText('Welcome Back!')).toBeVisible();
  });
});

