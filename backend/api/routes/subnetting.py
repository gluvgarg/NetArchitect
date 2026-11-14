"""Subnetting and VLSM Allocation routes.

Provides endpoints for Variable Length Subnet Masking (VLSM)
and CIDR address decomposition for hierarchical networks (RFC 1878, RFC 4632).
"""

from fastapi import APIRouter, HTTPException, status
from engines.vlsm_engine import VLSMEngine, InsufficientAddressSpaceError
from models.subnet import VLSMRequest, VLSMResponse

router = APIRouter()
vlsm_engine = VLSMEngine()


@router.get("/", summary="Subnetting Engine Information")
def subnetting_info():
    """Returns VLSM / Subnetting engine status and metadata."""
    return {
        "status": "active",
        "supported_addressing": ["IPv4 CIDR / VLSM (RFC 4632, RFC 1878)"],
        "gateway_convention": vlsm_engine.GATEWAY_CONVENTION,
        "message": "VLSM calculation engine is operational."
    }


@router.post(
    "/calculate",
    response_model=VLSMResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate VLSM Subnet Allocations",
    responses={
        200: {
            "description": "Successfully calculated VLSM allocation plan with IP ranges and metrics",
            "model": VLSMResponse,
        },
        400: {
            "description": "Insufficient address space in root network",
        },
        422: {
            "description": "Validation error (invalid CIDR, non-positive hosts, or duplicate subnet names)",
        },
    },
)
def calculate_vlsm(request: VLSMRequest):
    """Calculates an optimized VLSM subnet allocation plan for a root IPv4 network.

    Features:
    - Sorts subnet requirements in descending order of usable host count to prevent fragmentation.
    - Sizes each block to the smallest power of 2 accommodating required usable hosts plus network/broadcast IPs.
    - Sequentially allocates subnets with strict binary boundary alignment (N % B == 0).
    - Identifies remaining unallocated contiguous address blocks and efficiency metrics.
    - Assigns the first usable host IP as the default gateway.
    """
    try:
        result = vlsm_engine.calculate_vlsm(
            base_network=request.base_network,
            subnets_needed=request.subnets,
        )
        return result
    except InsufficientAddressSpaceError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_type": "InsufficientAddressSpaceError",
                "message": err.message,
                "root_network": err.root_network,
                "total_root_addresses": err.total_root_addresses,
                "total_required_addresses": err.total_required_addresses,
                "deficit": err.deficit,
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
    response_model=VLSMResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def calculate_vlsm_root(request: VLSMRequest):
    """Alias for POST /calculate to support base route POST."""
    return calculate_vlsm(request)
