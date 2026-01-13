import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


# -------------------------------------------------------------------
# Sanity checks (fail fast)
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
    """
    Internal helper for sending Brevo transactional emails.
    Raises RuntimeError on failure.
    """
    print("---- _send_email ----")
    print("to:", to)
    print("template_id:", template_id)
    print("params:", params)

    try:
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to}],
            template_id=template_id,
            params=params,
        )
        brevo.send_transac_email(email)
        print("✓ Brevo send_transac_email OK")

    except ApiException as e:
        print("❌ Brevo ApiException:", e)
        raise RuntimeError(
            f"Brevo email failed (template {template_id}): {e}"
        ) from e


# -------------------------------------------------------------------
# Public API
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


def send_enquiry_notification(
    *,
    business_email: str,
    business_name: str,
    customer_name: str,
    customer_email: str,
    message: str,
) -> None:
    print("=== send_enquiry_notification ===")
    print("business_email:", business_email)
    print("business_name:", business_name)

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


def send_booking_notification(
    *,
    business_email: str,
    business_name: str,
    customer_email: str | None,
    start_time: datetime,
) -> None:
    print("=== send_booking_notification ===")
    print("business_email:", business_email)
    print("business_name:", business_name)
    print("customer_email:", customer_email)
    print("start_time:", start_time, type(start_time))

    formatted_date = start_time.strftime("%A, %d %B %Y")
    formatted_time = start_time.strftime("%H:%M")

    # 1️⃣ Email business (CRITICAL)
    print("→ Sending BUSINESS booking email")

    _send_email(
        to=business_email,
        template_id=8,
        params={
            "BUSINESS_NAME": business_name,
            "FORMATTED_DATE": formatted_date,
            "FORMATTED_TIME": formatted_time,
            "CUSTOMER_EMAIL": customer_email,
        },
    )

    print("✓ Business booking email attempted")

    # 2️⃣ Email customer (NON-CRITICAL)
    if customer_email:
        print("→ Sending CUSTOMER booking email")

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
            print("✓ Customer booking email sent")

        except RuntimeError as e:
            print("⚠️ Customer email failed (non-critical):", e)
    else:
        print("⚠️ No customer email — skipping customer notification")

