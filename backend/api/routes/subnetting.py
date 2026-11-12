"""Subnetting and VLSM Allocation routes.

Provides endpoints for Variable Length Subnet Masking (VLSM)
and CIDR address decomposition for hierarchical networks.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Subnetting Engine Information")
def subnetting_info():
    """Returns VLSM / Subnetting engine status and metadata."""
    return {
        "status": "ready",
        "supported_addressing": ["IPv4 CIDR / VLSM", "IPv6 Prefix Delegation"],
        "message": "Subnetting / VLSM engine scaffold initialized."
    }
