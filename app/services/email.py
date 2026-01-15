from datetime import datetime, timezone
from app.core.utils import _send_email, _format_booking_time


#Send an email verification code during signup
def send_verification_email(*, user_email: str, code: str) -> None:
    _send_email(
        to=user_email,
        template_id=15,  # verify email
        params={
            "CODE": code,
            "DATE": datetime.now(timezone.utc).strftime("%d %B %Y"),
        },
    )


#Send a password reset code after identity verification
def send_password_reset_email(*, user_email: str, code: str) -> None:
    _send_email(
        to=user_email,
        template_id=16,  # reset password
        params={
            "CODE": code,
            "DATE": datetime.now(timezone.utc).strftime("%d %B %Y"),
        },
    )


#Notify a business that a new customer enquiry has been received
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


#Notify a customer that their booking request is pending confirmation
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


#Notify a business that a new booking request is awaiting action
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


#Notify a customer that their booking has been confirmed
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


#Notify a customer that their booking has been cancelled
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


#Notify a business that their subscription has been activated
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


#Notify a business that their subscription plan has changed
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


#Notify a business that their subscription has been cancelled
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


#Notify a business that their account has been paused due to payment issues
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


#Notify a business about a payment issue and remaining grace period
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