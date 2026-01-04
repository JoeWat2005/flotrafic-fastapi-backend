import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
BREVO_API_KEY = os.getenv("BREVO_API_KEY")

if EMAIL_ENABLED and not BREVO_API_KEY:
    raise RuntimeError("BREVO_API_KEY not set")


# -------------------------
# Brevo client setup
# -------------------------
config = sib_api_v3_sdk.Configuration()
config.api_key["api-key"] = BREVO_API_KEY
client = sib_api_v3_sdk.ApiClient(config)
brevo = sib_api_v3_sdk.TransactionalEmailsApi(client)


def send_template_email(
    *,
    to: str,
    template_id: int,
    params: dict,
):
    """
    Send a Brevo transactional email using a template.
    """

    if not EMAIL_ENABLED:
        print("📧 EMAIL (dev mode)")
        print("To:", to)
        print("Template ID:", template_id)
        print("Params:", params)
        print("📧 END EMAIL")
        return

    try:
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to}],
            template_id=template_id,
            params=dict(params),  # ✅ THIS FIXES BLANK VARIABLES
        )

        brevo.send_transac_email(email)

    except ApiException as e:
        print(f"❌ Brevo email failed: {e}")


