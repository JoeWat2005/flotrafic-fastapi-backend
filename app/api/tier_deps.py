from fastapi import Depends, HTTPException, status
from app.db.models import Business
from app.api.deps import get_current_business


def require_tier(*allowed_tiers: str):
    """
    Usage:
    Depends(require_tier("managed", "ai"))
    """

    def _check_tier(
        business: Business = Depends(get_current_business),
    ) -> Business:
        if business.tier not in allowed_tiers:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Your plan does not support this feature. "
                    f"Required: {', '.join(allowed_tiers)}"
                ),
            )

        return business

    return _check_tier
