"""Network Device Configuration routes.

Generates syntax-checked router/switch configurations (e.g. Cisco IOS CLI).
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Configuration Generator Information")
def configs_info():
    """Returns configuration generator status and supported targets."""
    return {
        "status": "ready",
        "supported_targets": ["Cisco IOS", "Standard CLI Scripts"],
        "message": "Configuration generator scaffold initialized."
    }
