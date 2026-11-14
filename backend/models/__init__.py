"""Pydantic schemas and domain models for NetArchitect."""

from models.scenario import NetworkProfileModel, ScenarioRequest
from models.media import (
    MediaRecommendationRequest,
    MediaRecommendationResponse,
    OpticalBudget,
    PreferredMedium,
)
from models.subnet import (
    SubnetRequirement,
    VLSMRequest,
    SubnetAllocation,
    VLSMResponse,
)
from models.routing import (
    RoutingRecommendationRequest,
    RoutingRecommendationResponse,
    AutonomousSystemInfo,
    OSPFAreaInfo,
    RoutingRequest,
    RoutingResponse,
)
from models.config import (
    VLANConfig,
    InterfaceConfig,
    OSPFNetworkConfig,
    OSPFConfig,
    BGPNeighborConfig,
    BGPNetworkConfig,
    BGPConfig,
    ConfigGenerationRequest,
    ConfigGenerationResponse,
    DeviceConfigGenerationRequest,
    DeviceConfigGenerationResponse,
    ConfigCommandExplanation,
)
from models.explanation import ExplanationModel

__all__ = [
    "NetworkProfileModel",
    "ScenarioRequest",
    "MediaRecommendationRequest",
    "MediaRecommendationResponse",
    "OpticalBudget",
    "PreferredMedium",
    "SubnetRequirement",
    "VLSMRequest",
    "SubnetAllocation",
    "VLSMResponse",
    "RoutingRecommendationRequest",
    "RoutingRecommendationResponse",
    "AutonomousSystemInfo",
    "OSPFAreaInfo",
    "RoutingRequest",
    "RoutingResponse",
    "VLANConfig",
    "InterfaceConfig",
    "OSPFNetworkConfig",
    "OSPFConfig",
    "BGPNeighborConfig",
    "BGPNetworkConfig",
    "BGPConfig",
    "ConfigGenerationRequest",
    "ConfigGenerationResponse",
    "DeviceConfigGenerationRequest",
    "DeviceConfigGenerationResponse",
    "ConfigCommandExplanation",
    "ExplanationModel",
]
