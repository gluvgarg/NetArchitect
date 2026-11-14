"""Pydantic models for Routing Protocol recommendations.

Academic Context:
Provides structured request and response models for routing architecture decisions,
evaluating autonomous system boundaries (RFC 4271) and interior link-state
hierarchy (RFC 2328).
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator


class RoutingRecommendationRequest(BaseModel):
    """Input parameters to determine optimal routing architecture."""

    network_name: str = Field(
        ...,
        min_length=1,
        description="Descriptive identifier for the target network",
        examples=["Campus-Core-Network"],
    )
    autonomous_system_count: int = Field(
        1,
        ge=1,
        description="Number of Autonomous Systems involved (must be >= 1)",
        examples=[1],
    )
    subnet_count: int = Field(
        ...,
        ge=1,
        description="Total number of layer 3 subnets in the routing domain (must be >= 1)",
        examples=[20],
    )
    site_count: int = Field(
        1,
        ge=1,
        description="Number of physical geographic sites/campuses (must be >= 1)",
        examples=[2],
    )
    has_external_as_boundary: bool = Field(
        False,
        description="True if peering across an external AS boundary or public provider",
    )
    ospf_areas_required: Optional[int] = Field(
        None,
        ge=1,
        description="Explicit number of internal OSPF areas required, if predetermined (must be >= 1)",
        examples=[3],
    )
    topology_description: Optional[str] = Field(
        None,
        description="Optional narrative description of network topology and constraints",
    )

    @field_validator("network_name")
    @classmethod
    def validate_network_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Network name cannot be empty or whitespace only.")
        return v.strip()


class AutonomousSystemInfo(BaseModel):
    """Autonomous System analysis and characteristics."""

    as_count: int = Field(..., description="Total count of Autonomous Systems")
    is_multi_as: bool = Field(..., description="Whether multiple ASes are present")
    has_external_boundary: bool = Field(..., description="Whether an external AS boundary exists")
    description: str = Field(..., description="Analysis of the AS boundary environment")


class OSPFAreaInfo(BaseModel):
    """OSPF area hierarchy and router role specifications."""

    area_count: Optional[int] = Field(None, description="Number of OSPF areas")
    backbone_area: str = Field("Area 0 (0.0.0.0)", description="Designated backbone area")
    requires_area_0: bool = Field(True, description="Whether Area 0 backbone is required")
    requires_abr: bool = Field(False, description="Whether Area Border Routers (ABRs) are required")
    area_roles: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of area identifiers to architectural roles",
    )
    design_notes: str = Field(..., description="Architectural guidance on area hierarchy")


class RoutingRecommendationResponse(BaseModel):
    """Complete routing protocol recommendation with academic rationale."""

    network_name: str = Field(..., description="Name of the evaluated network")
    recommended_protocol: str = Field(
        ...,
        description="Recommended routing protocol/architecture",
        examples=["Single-Area OSPF (Area 0)", "Multi-Area OSPF", "eBGP (External Border Gateway Protocol)"],
    )
    architecture_type: str = Field(
        ...,
        description="Classification: Interior Gateway Protocol (IGP) vs Exterior Gateway Protocol (EGP)",
    )
    reason_for_selection: str = Field(
        ...,
        description="Primary academic and technical justification for recommendation",
    )
    autonomous_system_info: AutonomousSystemInfo = Field(
        ...,
        description="AS boundary analysis",
    )
    ospf_area_info: Optional[OSPFAreaInfo] = Field(
        None,
        description="OSPF area details if OSPF is recommended or evaluated",
    )
    area_0_required: bool = Field(
        ...,
        description="Whether an Area 0 backbone is mandatory in this architecture",
    )
    abr_required: bool = Field(
        ...,
        description="Whether Area Border Routers (ABRs) are mandatory in this architecture",
    )
    routing_characteristics: List[str] = Field(
        ...,
        description="Key protocol mechanics (e.g. link-state LSDB, Dijkstra SPF, path vector)",
    )
    advantages: List[str] = Field(
        ...,
        description="Benefits of the recommended routing architecture",
    )
    limitations: List[str] = Field(
        ...,
        description="Operational limitations, scaling trade-offs, and design caveats",
    )
    standards_and_rfcs: List[str] = Field(
        ...,
        description="Applicable IETF Standards and RFC citations",
    )
    explainability_record_id: Optional[str] = Field(
        None,
        description="UUID reference to the recorded audit log in ExplainabilityEngine",
    )
    requires_design_review: bool = Field(
        False,
        description="True if topology input was ambiguous, contradictory, or requires human design review",
    )


# Backward-compatible aliases for existing imports
RoutingRequest = RoutingRecommendationRequest
RoutingResponse = RoutingRecommendationResponse
