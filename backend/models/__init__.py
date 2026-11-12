"""Pydantic schemas and domain models for NetArchitect."""

from models.scenario import NetworkProfileModel, ScenarioRequest
from models.media import MediaRecommendationRequest, MediaRecommendationResponse
from models.subnet import VLSMRequest, SubnetAllocation
from models.routing import RoutingRequest, RoutingResponse
from models.config import ConfigGenerationRequest, ConfigGenerationResponse
from models.explanation import ExplanationModel

__all__ = [
    "NetworkProfileModel",
    "ScenarioRequest",
    "MediaRecommendationRequest",
    "MediaRecommendationResponse",
    "VLSMRequest",
    "SubnetAllocation",
    "RoutingRequest",
    "RoutingResponse",
    "ConfigGenerationRequest",
    "ConfigGenerationResponse",
    "ExplanationModel",
]
