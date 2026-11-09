# Email Notification Setup

This project supports email notifications through the Brevo transactional email service.

## Configuration

1. Create a Brevo account.
2. Verify your sender email address.
3. Generate a Brevo API key.
4. Copy `.env.example` to `.env` in the project root.
5. Add your actual credentials to `.env`.

## Environment Variables

- `BREVO_API_KEY`
- `BREVO_SENDER_EMAIL`
- `BREVO_SENDER_NAME`
- `BREVO_INSTITUTION_NAME`
- `BREVO_MENTOR_NAME`

**Security:** Never upload your `.env` file or share your API key publicly. The `.env` file is excluded through `.gitignore`.