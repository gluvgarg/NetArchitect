"""Pydantic models for Physical Transmission Media recommendations."""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class PreferredMedium(str, Enum):
    """Supported explicit medium options."""
    COPPER = "copper"
    MULTIMODE_FIBER = "multimode_fiber"
    SINGLEMODE_FIBER = "singlemode_fiber"
    FIBER = "fiber"


class OpticalBudget(BaseModel):
    """Optical link power budget details for single-mode fiber links."""
    tx_power_min_dbm: float = Field(..., description="Transmitter minimum output power in dBm")
    rx_sensitivity_dbm: float = Field(..., description="Receiver sensitivity threshold in dBm")
    power_budget_db: float = Field(..., description="Available optical power budget in dB")
    attenuation_coefficient_db_per_km: float = Field(..., description="Fiber attenuation coefficient in dB/km")
    fiber_loss_db: float = Field(..., description="Estimated fiber attenuation loss in dB")
    connector_loss_db: float = Field(..., description="Estimated connector insertion loss in dB")
    safety_margin_db: float = Field(..., description="Engineering safety / aging margin in dB")
    total_estimated_loss_db: float = Field(..., description="Total link loss in dB")
    power_margin_db: float = Field(..., description="Remaining unallocated optical power margin in dB")
    is_budget_sufficient: bool = Field(..., description="True if total estimated loss <= power budget")
    budget_status: str = Field("sufficient", description="'sufficient' or 'insufficient_under_conservative_assumptions'")
    engineering_recommendation: Optional[str] = Field(None, description="Guidance if installation margin is insufficient")


class MediaRecommendationRequest(BaseModel):
    """Input criteria for Layer 1 transmission media selection."""
    distance_meters: float = Field(..., description="Physical distance in meters (must be > 0)")
    preferred_medium: Optional[str] = Field(None, description="Optional preferred medium: 'copper', 'multimode_fiber', 'singlemode_fiber', or 'fiber'")
    required_bandwidth_mbps: float = Field(10000.0, gt=0, description="Desired throughput in Mbps (default: 10000 / 10 Gbps)")
    environment: str = Field("indoor", description="'indoor', 'industrial', or 'outdoor'")
    budget_priority: str = Field("balanced", description="'low_cost', 'balanced', or 'high_performance'")

    @field_validator("distance_meters")
    @classmethod
    def validate_positive_distance(cls, v: float) -> float:
        """Enforce strictly positive distance."""
        if v is None or v <= 0:
            raise ValueError(f"Distance must be positive and greater than 0 meters. Received: {v}")
        return v

    @field_validator("preferred_medium")
    @classmethod
    def validate_preferred_medium(cls, v: Optional[str]) -> Optional[str]:
        """Validate preferred medium strings."""
        if v is None:
            return None
        v_clean = v.strip().lower()
        valid_options = {
            "copper", "cat6a", "twisted_pair",
            "multimode_fiber", "om4", "mmf", "fiber_multimode",
            "singlemode_fiber", "os2", "smf", "fiber_singlemode",
            "fiber"
        }
        if v_clean not in valid_options:
            raise ValueError(
                f"Invalid preferred_medium '{v}'. Supported options: 'copper', 'multimode_fiber', 'singlemode_fiber', 'fiber'."
            )
        return v_clean


class MediaRecommendationResponse(BaseModel):
    """Recommended media specifications, standards, and technical justification."""
    input_distance_meters: float
    requested_medium: Optional[str] = None
    selected_medium: str
    technology_standard: str
    wavelength_nm: Optional[int] = None
    max_supported_distance_meters: float
    maximum_bandwidth_mbps: float
    attenuation_rating: str
    cost_index: str
    technical_reasoning: str
    why_alternatives_not_selected: Dict[str, str]
    assumptions_and_limitations: List[str]
    standards_and_rfcs: List[str]
    optical_budget: Optional[OpticalBudget] = None
    explanation_record_id: Optional[str] = None

    # Backward compatibility attributes
    recommended_media: Optional[str] = None
    cable_standard: Optional[str] = None
    rationale: Optional[str] = None
