# Development Email Setup

## Current Status

The OTP email system is set up, but **email sending is in development mode**.

### Development Mode (Default)

When SMTP credentials are not configured, the OTP will be **printed to the backend console** instead of sent via email.

**To see your OTP:**
1. Start the backend server
2. Request an OTP from the frontend
3. Check the backend terminal/console
4. Look for the OTP code in the output

Example output:
```
============================================================
[DEV MODE] OTP Email would be sent to: user@example.com
[DEV MODE] Verification Code: 123456
[DEV MODE] To enable real email sending, configure SMTP settings in .env
============================================================
```

## Enable Real Email Sending

To send actual emails, configure SMTP settings:

### Option 1: Gmail (Recommended for Development)

1. **Create a `.env` file** in the `backend` directory:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

2. **Generate a Gmail App Password:**
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and your device
   - Copy the 16-character password
   - Use this as `SMTP_PASSWORD`

### Option 2: Other Email Providers

For other providers, update the settings:

```env
SMTP_HOST=smtp.yourprovider.com
SMTP_PORT=587  # or 465 for SSL
SMTP_USER=your-email@yourprovider.com
SMTP_PASSWORD=your-password
```

### Option 3: Development Email Services

For testing, you can use services like:
- **Mailtrap** (https://mailtrap.io) - Free for development
- **MailHog** - Local email testing
- **Ethereal Email** - Quick testing

## Testing

1. **Without Email Setup (Dev Mode):**
   ```powershell
   # Backend will print OTP to console
   cd backend
   & "$env:APPDATA\Python\Python313\Scripts\poetry.exe" run uvicorn app.main:app --reload --port 8000
   ```

2. **With Email Setup:**
   - Configure `.env` file with SMTP settings
   - Restart backend server
   - OTPs will be sent via email

## Troubleshooting

### OTP not showing in console?
- Make sure backend server is running
- Check backend terminal output
- Verify the `/api/auth/send-otp` endpoint is being called

### Email sending fails?
- Check SMTP credentials in `.env`
- Verify firewall/network allows SMTP connections
- Check spam folder for emails
- Backend will fallback to console printing if email fails

### For Production
- Use a proper email service (SendGrid, AWS SES, etc.)
- Never commit `.env` files with real credentials
- Use environment variables in production hosting

