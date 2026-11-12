"""Pydantic models for Network Scenarios and Profiles."""

from typing import List, Optional
from pydantic import BaseModel, Field


class NetworkProfileModel(BaseModel):
    """Network Profile description model."""
    id: str
    name: str
    full_name: str
    scope: str
    max_diameter_meters: float
    bandwidth_target: str
    typical_latency_ms: str
    physical_media: List[str]
    recommended_routing: str
    layer_2_features: List[str]
    addressing_strategy: str
    description: str


class ScenarioRequest(BaseModel):
    """Input parameters to assess network profile requirements."""
    campus_name: str = Field(..., description="Organization or project identifier")
    max_distance_meters: float = Field(..., ge=1, description="Furthest link distance in meters")
    total_endpoints: int = Field(..., ge=1, description="Estimated total hosts/devices")
    budget_priority: str = Field("balanced", description="'low_cost', 'balanced', or 'high_performance'")
