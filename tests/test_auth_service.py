"""End-to-end style auth service tests."""

import pytest

from app.services.auth_service import AuthService
from app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_signup_verify_login_logout_flow(db_session, redis_client, monkeypatch):
    """Test signup -> verify email -> login -> logout flow.

    Args:
        db_session: Async SQLAlchemy test session.
        redis_client: Fake Redis client.
        monkeypatch: Pytest monkeypatch fixture.
    Returns:
        None: Asserts successful end-to-end flow.
    """
    captured = {}

    def fake_send_verification(_self, recipient: str, token: str) -> None:
        """Capture email verification token sent by service.

        Args:
            recipient: Email recipient.
            token: Verification token.
        Returns:
            None: Stores token in captured dict.
        """
        captured["recipient"] = recipient
        captured["token"] = token

    monkeypatch.setattr(EmailService, "send_verification_email", fake_send_verification)

    service = AuthService()
    await service.signup(db_session, "user1@example.com", "Str0ngPassword!", "User One")
    assert captured["recipient"] == "user1@example.com"

    verified = await service.verify_email(db_session, captured["token"])
    assert verified is True

    logged_in = await service.login(db_session, redis_client, "user1@example.com", "Str0ngPassword!")
    assert logged_in is not None
    assert "access_token" in logged_in and "refresh_token" in logged_in

    logged_out = await service.logout(db_session, redis_client, logged_in["refresh_token"])
    assert logged_out is True

    claims = await service.verify_access_token(db_session, redis_client, logged_in["access_token"])
    assert claims is None


@pytest.mark.asyncio
async def test_forgot_and_reset_password_flow(db_session, redis_client, monkeypatch):
    """Test forgot password -> reset password -> login with new password.

    Args:
        db_session: Async SQLAlchemy test session.
        redis_client: Fake Redis client.
        monkeypatch: Pytest monkeypatch fixture.
    Returns:
        None: Asserts password reset flow works.
    """
    service = AuthService()
    verify_capture = {}
    reset_capture = {}

    def fake_send_verification(_self, recipient: str, token: str) -> None:
        """Capture verification token for test setup.

        Args:
            recipient: Email recipient.
            token: Verification token.
        Returns:
            None: Stores token for assertions.
        """
        verify_capture["recipient"] = recipient
        verify_capture["token"] = token

    def fake_send_reset(_self, recipient: str, token: str) -> None:
        """Capture password reset token.

        Args:
            recipient: Email recipient.
            token: Password reset token.
        Returns:
            None: Stores token for assertions.
        """
        reset_capture["recipient"] = recipient
        reset_capture["token"] = token

    monkeypatch.setattr(EmailService, "send_verification_email", fake_send_verification)
    monkeypatch.setattr(EmailService, "send_password_reset_email", fake_send_reset)

    await service.signup(db_session, "user2@example.com", "StartPass1!", "User Two")
    await service.verify_email(db_session, verify_capture["token"])
    await service.forgot_password(db_session, "user2@example.com")
    assert reset_capture["recipient"] == "user2@example.com"

    ok = await service.reset_password(db_session, reset_capture["token"], "NewPass2!")
    assert ok is True

    login_with_old = await service.login(db_session, redis_client, "user2@example.com", "StartPass1!")
    assert login_with_old is None

    login_with_new = await service.login(db_session, redis_client, "user2@example.com", "NewPass2!")
    assert login_with_new is not None


@pytest.mark.asyncio
async def test_request_otp_and_login_otp_flow(db_session, redis_client, monkeypatch):
    """Test OTP request and OTP-based login flow.

    Args:
        db_session: Async SQLAlchemy test session.
        redis_client: Fake Redis client.
        monkeypatch: Pytest monkeypatch fixture.
    Returns:
        None: Asserts OTP login works.
    """
    service = AuthService()
    verify_capture = {}
    otp_capture = {}

    def fake_send_verification(_self, recipient: str, token: str) -> None:
        """Capture verification token for test setup.

        Args:
            recipient: Email recipient.
            token: Verification token.
        Returns:
            None: Stores token for assertions.
        """
        verify_capture["recipient"] = recipient
        verify_capture["token"] = token

    def fake_send_otp(_self, recipient: str, otp: str) -> None:
        """Capture OTP code to complete login test.

        Args:
            recipient: Email recipient.
            otp: OTP code.
        Returns:
            None: Stores OTP for assertions.
        """
        otp_capture["recipient"] = recipient
        otp_capture["otp"] = otp

    monkeypatch.setattr(EmailService, "send_verification_email", fake_send_verification)
    monkeypatch.setattr(EmailService, "send_otp_email", fake_send_otp)

    await service.signup(db_session, "user3@example.com", "OtpPass1!", "User Three")
    await service.verify_email(db_session, verify_capture["token"])
    await service.request_otp(db_session, "user3@example.com")
    assert otp_capture["recipient"] == "user3@example.com"

    logged_in = await service.login_with_otp(db_session, redis_client, "user3@example.com", otp_capture["otp"])
    assert logged_in is not None
    assert "access_token" in logged_in
