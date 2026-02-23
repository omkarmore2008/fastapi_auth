"""Email service used for verification, reset, and OTP delivery."""

import smtplib
from email.message import EmailMessage

from app.core.config import get_settings


class EmailService:
    """Simple SMTP email sender service."""

    def __init__(self) -> None:
        """Initialize email service settings.

        Args:
            None
        Returns:
            None: Creates a configured email service instance.
        """
        self.settings = get_settings()

    def send_email(self, recipient: str, subject: str, body: str) -> None:
        """Send a plain-text email message.

        Args:
            recipient: Destination email address.
            subject: Email subject line.
            body: Plain text body content.
        Returns:
            None: Sends email through configured SMTP server.
        """
        msg = EmailMessage()
        msg["From"] = self.settings.MAIL_FROM
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT) as smtp:
            if self.settings.SMTP_STARTTLS:
                smtp.starttls()
            if self.settings.SMTP_USERNAME:
                smtp.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
            smtp.send_message(msg)

    def send_verification_email(self, recipient: str, token: str) -> None:
        """Send signup verification email.

        Args:
            recipient: Destination email address.
            token: Raw verification token string.
        Returns:
            None: Sends verification instructions via email.
        """
        body = (
            "Welcome! Verify your account with this token:\n\n"
            f"{token}\n\n"
            "Use it at POST /auth/verify-email."
        )
        self.send_email(recipient, "Verify your account", body)

    def send_password_reset_email(self, recipient: str, token: str) -> None:
        """Send password reset email.

        Args:
            recipient: Destination email address.
            token: Raw reset token string.
        Returns:
            None: Sends password reset instructions via email.
        """
        body = (
            "Reset your password with this token:\n\n"
            f"{token}\n\n"
            "Use it at POST /auth/reset-password."
        )
        self.send_email(recipient, "Password reset token", body)

    def send_otp_email(self, recipient: str, otp: str) -> None:
        """Send one-time login code.

        Args:
            recipient: Destination email address.
            otp: Numeric OTP code.
        Returns:
            None: Sends OTP instructions via email.
        """
        body = f"Your login OTP code is: {otp}\n\nThis code will expire in a few minutes."
        self.send_email(recipient, "Your login OTP", body)
