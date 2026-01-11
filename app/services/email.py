import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from datetime import datetime, timezone


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
# Public API
# -------------------------------------------------------------------
def send_verification_email(*, to: str, code: str) -> None:
    """
    Send email verification code to a new business.
    """

    try:
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to}],
            template_id=5,  # 🔁 replace with your real Brevo template ID
            params={
                "VERIFICATION_CODE": code,
                "DATE": datetime.now(timezone.utc).strftime("%d %B %Y"),
            },
        )

        brevo.send_transac_email(email)

    except ApiException as e:
        raise RuntimeError(f"Brevo verification email failed: {e}") from e
    

def send_password_reset_email(*, to: str, code: str) -> None:
    try:
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to}],
            template_id=6,
            params={
                "RESET_CODE": code,
                "DATE": datetime.now(timezone.utc).strftime("%d %B %Y"),
            },
        )
        
        brevo.send_transac_email(email)

    except ApiException as e:
        raise RuntimeError(f"Brevo password-reset email failed: {e}") from e
