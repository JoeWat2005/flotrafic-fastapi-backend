import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


# -------------------------------------------------------------------
# Sanity checks
# -------------------------------------------------------------------
if not settings.BREVO_API_KEY:
    raise RuntimeError("BREVO_API_KEY is not set")


# -------------------------------------------------------------------
# Brevo client setup
# -------------------------------------------------------------------
config = sib_api_v3_sdk.Configuration()
config.api_key["api-key"] = settings.BREVO_API_KEY

client = sib_api_v3_sdk.ApiClient(config)
brevo = sib_api_v3_sdk.TransactionalEmailsApi(client)


# -------------------------------------------------------------------
# Internal helper (ONLY place that talks to Brevo)
# -------------------------------------------------------------------
def _send_email(*, to: str, template_id: int, params: dict[str, Any]) -> None:
    try:
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to}],
            template_id=template_id,
            params=params,
        )
        brevo.send_transac_email(email)

    except ApiException as e:
        raise RuntimeError(
            f"Brevo email failed (template {template_id})"
        ) from e


# =========================================================
# AUTH EMAILS
# =========================================================
def send_verification_email(*, user_email: str, code: str) -> None:
    _send_email(
        to=user_email,
        template_id=15,  # verify email
        params={
            "CODE": code,
            "DATE": datetime.now(timezone.utc).strftime("%d %B %Y"),
        },
    )


def send_password_reset_email(*, user_email: str, code: str) -> None:
    _send_email(
        to=user_email,
        template_id=16,  # reset password
        params={
            "CODE": code,
            "DATE": datetime.now(timezone.utc).strftime("%d %B %Y"),
        },
    )


# =========================================================
# ENQUIRIES
# =========================================================
def send_enquiry_notification(
    *,
    business_email: str,
    customer_name: str,
    customer_email: str,
    message: str,
) -> None:
    _send_email(
        to=business_email,
        template_id=14,  # enquiry received (business)
        params={
            "CUSTOMER_NAME": customer_name,
            "CUSTOMER_EMAIL": customer_email,
            "MESSAGE": message,
        },
    )


# =========================================================
# BOOKINGS — STATE AWARE
# =========================================================
def _format_booking_time(start_time: datetime) -> tuple[str, str]:
    return (
        start_time.strftime("%A, %d %B %Y"),
        start_time.strftime("%H:%M"),
    )


# ---------------------------------------------------------
# Booking created → PENDING
# ---------------------------------------------------------
def send_booking_pending_customer(
    *,
    customer_email: str,
    business_name: str,
    start_time: datetime,
) -> None:
    formatted_date, formatted_time = _format_booking_time(start_time)

    _send_email(
        to=customer_email,
        template_id=10,  # booking pending (customer)
        params={
            "BUSINESS_NAME": business_name,
            "FORMATTED_DATE": formatted_date,
            "FORMATTED_TIME": formatted_time,
        },
    )


def send_booking_pending_business(
    *,
    business_email: str,
    business_name: str,
    customer_email: str | None,
    start_time: datetime,
) -> None:
    formatted_date, formatted_time = _format_booking_time(start_time)

    _send_email(
        to=business_email,
        template_id=11,  # booking pending (business)
        params={
            "BUSINESS_NAME": business_name,
            "FORMATTED_DATE": formatted_date,
            "FORMATTED_TIME": formatted_time,
            "CUSTOMER_EMAIL": customer_email or "",
        },
    )


# ---------------------------------------------------------
# Booking confirmed
# ---------------------------------------------------------
def send_booking_confirmed_customer(
    *,
    customer_email: str,
    business_name: str,
    business_email: str,
    start_time: datetime,
) -> None:
    formatted_date, formatted_time = _format_booking_time(start_time)

    _send_email(
        to=customer_email,
        template_id=12,  # booking confirmed (customer)
        params={
            "BUSINESS_NAME": business_name,
            "FORMATTED_DATE": formatted_date,
            "FORMATTED_TIME": formatted_time,
            "BUSINESS_EMAIL": business_email,
        },
    )


# ---------------------------------------------------------
# Booking cancelled
# ---------------------------------------------------------
def send_booking_cancelled_customer(
    *,
    customer_email: str,
    business_name: str,
    start_time: datetime,
) -> None:
    formatted_date, formatted_time = _format_booking_time(start_time)

    _send_email(
        to=customer_email,
        template_id=13,  # booking cancelled (customer)
        params={
            "BUSINESS_NAME": business_name,
            "FORMATTED_DATE": formatted_date,
            "FORMATTED_TIME": formatted_time,
        },
    )


# =========================================================
# SUBSCRIPTION / BILLING
# =========================================================
def send_subscription_activated_email(
    *,
    business_email: str,
    tier: str,
) -> None:
    _send_email(
        to=business_email,
        template_id=17,  # subscription activated
        params={
            "TIER": tier.capitalize(),
            "DATE": datetime.now(timezone.utc).strftime("%d %B %Y"),
        },
    )


def send_subscription_plan_changed_email(
    *,
    business_email: str,
    old_tier: str,
    new_tier: str,
) -> None:
    _send_email(
        to=business_email,
        template_id=18,  # subscription plan changed
        params={
            "OLD_TIER": old_tier.capitalize(),
            "NEW_TIER": new_tier.capitalize(),
            "DATE": datetime.now(timezone.utc).strftime("%d %B %Y"),
        },
    )


def send_subscription_cancelled_email(
    *,
    business_email: str,
) -> None:
    _send_email(
        to=business_email,
        template_id=19,  # subscription cancelled
        params={
            "DATE": datetime.now(timezone.utc).strftime("%d %B %Y"),
        },
    )


def send_account_paused_email(
    *,
    business_email: str,
) -> None:
    _send_email(
        to=business_email,
        template_id=20,  # account paused
        params={
            "DATE": datetime.now(timezone.utc).strftime("%d %B %Y"),
        },
    )


def send_payment_issue_email(
    *,
    business_email: str,
    status: str,
    grace_days: int,
) -> None:
    _send_email(
        to=business_email,
        template_id=21,  # payment issue
        params={
            "STATUS": status,
            "GRACE_DAYS": grace_days,
            "DATE": datetime.now(timezone.utc).strftime("%d %B %Y"),
        },
    )


