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


# -------------------------------------------------------------------
# Auth emails
# -------------------------------------------------------------------
def send_verification_email(*, user_email: str, code: str) -> None:
    _send_email(
        to=user_email,
        template_id=5,
        params={
            "VERIFICATION_CODE": code,
            "DATE": datetime.now(timezone.utc).strftime("%d %B %Y"),
        },
    )


def send_password_reset_email(*, user_email: str, code: str) -> None:
    _send_email(
        to=user_email,
        template_id=6,
        params={
            "RESET_CODE": code,
            "DATE": datetime.now(timezone.utc).strftime("%d %B %Y"),
        },
    )


# -------------------------------------------------------------------
# Enquiries
# -------------------------------------------------------------------
def send_enquiry_notification(
    *,
    business_email: str,
    business_name: str,
    customer_name: str,
    customer_email: str,
    message: str,
) -> None:
    _send_email(
        to=business_email,
        template_id=7,
        params={
            "BUSINESS_NAME": business_name,
            "CUSTOMER_NAME": customer_name,
            "CUSTOMER_EMAIL": customer_email,
            "MESSAGE": message,
        },
    )


# -------------------------------------------------------------------
# Bookings
# -------------------------------------------------------------------
def send_booking_notification(
    *,
    business_email: str,
    business_name: str,
    customer_email: str | None,
    start_time: datetime,
) -> None:
    formatted_date = start_time.strftime("%A, %d %B %Y")
    formatted_time = start_time.strftime("%H:%M")

    # Business notification (CRITICAL)
    _send_email(
        to=business_email,
        template_id=8,
        params={
            "BUSINESS_NAME": business_name,
            "FORMATTED_DATE": formatted_date,
            "FORMATTED_TIME": formatted_time,
            "CUSTOMER_EMAIL": customer_email or "",
        },
    )

    # Customer confirmation (NON-CRITICAL)
    if customer_email:
        try:
            _send_email(
                to=customer_email,
                template_id=9,
                params={
                    "BUSINESS_NAME": business_name,
                    "FORMATTED_DATE": formatted_date,
                    "FORMATTED_TIME": formatted_time,
                    "BUSINESS_EMAIL": business_email,
                },
            )
        except RuntimeError:
            pass


# -------------------------------------------------------------------
# Subscription lifecycle (PRODUCT state, not billing)
# -------------------------------------------------------------------
def send_subscription_activated_email(
    *,
    business_email: str,
    tier: str,
) -> None:
    _send_email(
        to=business_email,
        template_id=10,
        params={
            "TIER": tier.capitalize(),
            "DATE": datetime.now(timezone.utc).strftime("%d %B %Y"),
        },
    )


def send_subscription_cancelled_email(
    *,
    business_email: str,
) -> None:
    _send_email(
        to=business_email,
        template_id=11,
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
        template_id=12,
        params={
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
        template_id=13,  # Subscription plan changed
        params={
            "OLD_TIER": old_tier.capitalize(),
            "NEW_TIER": new_tier.capitalize(),
            "DATE": datetime.now(timezone.utc).strftime("%d %B %Y"),
        },
    )
