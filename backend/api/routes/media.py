"""Physical Transmission Media Recommendation routes.

Evaluates transmission media (Twisted Pair Copper, Multimode Fiber, Single-mode Fiber)
based on link distance, signal attenuation, modal/chromatic dispersion, and explicit constraints.
"""

from fastapi import APIRouter, HTTPException, status
from engines.media_engine import MediaEngine, PhysicalDistanceViolationError
from models.media import MediaRecommendationRequest, MediaRecommendationResponse

router = APIRouter()
media_engine = MediaEngine()


@router.get("/", summary="Transmission Media Information")
def media_info():
    """Returns transmission media recommendation engine metadata."""
    return {
        "status": "ready",
        "supported_media": [
            "Cat6a Balanced Twisted Pair (IEEE 802.3an, 10GBASE-T, <= 100m)",
            "OM4 Multimode Optical Fiber (IEEE 802.3ae, 10GBASE-SR, 850 nm, <= 400m)",
            "OS2 Single-Mode Optical Fiber (IEEE 802.3ae, 10GBASE-LR, 1310 nm, <= 10 km)",
            "OS2 Single-Mode Optical Fiber Extended (IEEE 802.3ae, 10GBASE-ER, 1550 nm, <= 40 km)"
        ],
        "message": "Physical media recommendation engine active."
    }


@router.post(
    "/recommend",
    response_model=MediaRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Recommend Physical Transmission Media",
    responses={
        200: {
            "description": "Successful media recommendation with technical reasoning and standards citation",
            "model": MediaRecommendationResponse,
        },
        400: {
            "description": "Physical distance violation (e.g. copper requested beyond 100m channel reach)",
        },
        422: {
            "description": "Validation error (non-positive distance or unrecognized preferred medium)",
        },
    },
)
def recommend_media(request: MediaRecommendationRequest):
    """Calculates optimal physical transmission media given distance and constraints.

    Enforces IEEE 802.3 channel length constraints:
    - Distance <= 100m: Cat6a Copper (10GBASE-T)
    - 100m < Distance <= 400m: OM4 Multimode Fiber (10GBASE-SR, 850 nm)
    - Distance > 400m: OS2 Single-mode Fiber (10GBASE-LR, 1310 nm optical budget)
    """
    try:
        result = media_engine.recommend_media(
            distance_meters=request.distance_meters,
            preferred_medium=request.preferred_medium,
            required_bandwidth_mbps=request.required_bandwidth_mbps,
            environment=request.environment,
            budget_priority=request.budget_priority,
        )
        return result
    except PhysicalDistanceViolationError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_type": "PhysicalDistanceViolationError",
                "message": err.message,
                "requested_medium": err.requested_medium,
                "distance_meters": err.distance_meters,
                "max_distance_meters": err.max_distance_meters,
                "attenuation_explanation": err.attenuation_explanation,
            },
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_type": "ValidationError",
                "message": str(err),
            },
        )


@router.post(
    "/",
    response_model=MediaRecommendationResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def recommend_media_root(request: MediaRecommendationRequest):
    """Alias for POST /recommend to support base route POST."""
    return recommend_media(request)
