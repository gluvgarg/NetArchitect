"""Pydantic models for Routing Protocol recommendations."""

from typing import List, Optional
from pydantic import BaseModel, Field


class RoutingRequest(BaseModel):
    """Input parameters to determine optimal routing architecture."""
    network_scope: str = Field(..., description="'lan', 'man', or 'wan'")
    router_count: int = Field(..., ge=1, description="Count of routing nodes")
    is_multi_vendor: bool = Field(True, description="Multi-vendor environment requiring open standards")
    requires_fast_convergence: bool = Field(True, description="Needs sub-second link-state convergence")
    is_external_peering: bool = Field(False, description="Peering with external Autonomous Systems")


class RoutingResponse(BaseModel):
    """Routing protocol recommendation with parameters."""
    recommended_protocol: str
    protocol_type: str
    administrative_distance: int
    metric_type: str
    convergence_speed: str
    scalability_notes: str
