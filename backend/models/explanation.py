"""Pydantic model for Explainability Records."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ExplanationModel(BaseModel):
    """Schema representing an academic engineering decision explanation."""
    record_id: str
    timestamp: str
    engine_name: str
    input_conditions: Dict[str, Any]
    selected_recommendation: Dict[str, Any]
    technical_reasoning: str
    standards_and_rfcs: List[str]
