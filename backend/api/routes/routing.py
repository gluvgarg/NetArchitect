"""Routing Protocol Recommendation routes.

Provides endpoints for recommending Interior Gateway Protocols (IGP)
and Exterior Gateway Protocols (EGP) such as OSPF, BGP, RIP, and static routing.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Routing Protocol Engine Information")
def routing_info():
    """Returns routing protocol recommendation metadata."""
    return {
        "status": "ready",
        "supported_protocols": ["OSPF (RFC 2328)", "BGP (RFC 4271)", "Static Routing"],
        "message": "Routing protocol engine scaffold initialized."
    }
