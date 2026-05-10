"""
Email Service — handles sending outreach emails.
"""


class EmailService:
    """Service for sending emails via SMTP or a transactional email provider."""

    def __init__(self):
        # TODO: configure SMTP / SendGrid / Resend credentials
        pass

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        """
        Send an email.

        Returns:
            True if the email was sent successfully.
        """
        # TODO: implement actual email sending
        print(f"📧 [Placeholder] Would send email to {to}: {subject}")
        return True
