"""Routing Protocol Recommendation routes.

Provides endpoints for recommending Interior Gateway Protocols (IGP)
and Exterior Gateway Protocols (EGP) such as Single-Area OSPF, Multi-Area OSPF,
and eBGP (RFC 2328, RFC 4271).
"""

from fastapi import APIRouter, HTTPException, status
from engines.routing_engine import RoutingEngine
from models.routing import (
    RoutingRecommendationRequest,
    RoutingRecommendationResponse,
)

router = APIRouter()
routing_engine = RoutingEngine()


@router.get("/", summary="Routing Protocol Engine Information")
def routing_info():
    """Returns routing protocol recommendation metadata."""
    return {
        "status": "ready",
        "supported_architectures": [
            "Single-Area OSPF (Area 0, RFC 2328, < 50 subnets)",
            "Multi-Area OSPF (Area 0 Backbone + ABRs, RFC 2328)",
            "eBGP (Inter-AS Border Peering, RFC 4271)",
        ],
        "scalability_thresholds": {
            "single_area_max_subnets": routing_engine.SINGLE_AREA_MAX_SUBNETS,
        },
        "message": "Routing protocol engine active.",
    }


@router.post(
    "/recommend",
    response_model=RoutingRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Recommend Routing Architecture",
    responses={
        200: {
            "description": "Deterministic routing protocol recommendation with technical rationale and standards citation",
            "model": RoutingRecommendationResponse,
        },
        422: {
            "description": "Validation error (non-positive counts, invalid parameters, or malformed request)",
        },
    },
)
def recommend_routing(request: RoutingRecommendationRequest):
    """Recommends an optimal routing protocol architecture based on network topology.

    Precedence Hierarchy:
    - Multiple ASes or external boundary -> eBGP (RFC 4271)
    - Single AS with explicit multi-area requirement -> Multi-Area OSPF (RFC 2328)
    - Single AS with < 50 subnets -> Single-Area OSPF Area 0 (RFC 2328)
    - Single AS with >= 50 subnets without area partitioning -> Design Review Required
    """
    try:
        result = routing_engine.recommend_routing(
            network_name=request.network_name,
            autonomous_system_count=request.autonomous_system_count,
            subnet_count=request.subnet_count,
            site_count=request.site_count,
            has_external_as_boundary=request.has_external_as_boundary,
            ospf_areas_required=request.ospf_areas_required,
            topology_description=request.topology_description,
        )
        return result
    except ValueError as err:
        http_status = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
        raise HTTPException(
            status_code=http_status,
            detail={
                "error_type": "ValidationError",
                "message": str(err),
            },
        )


@router.post(
    "/",
    response_model=RoutingRecommendationResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def recommend_routing_root(request: RoutingRecommendationRequest):
    """Alias for POST /recommend to support base route POST."""
    return recommend_routing(request)
