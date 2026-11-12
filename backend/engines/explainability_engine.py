"""Explainability Engine for NetArchitect.

Academic Context:
Provides traceable, academically rigorous engineering justifications for all
decisions made by NetArchitect engines. Records input constraints, selected
options, technical reasoning, and governing RFC/IEEE standards to facilitate
student learning and project defense demonstrations.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4


class ExplanationRecord:
    """Represents an explainable decision log entry."""

    def __init__(
        self,
        engine_name: str,
        input_conditions: Dict[str, Any],
        selected_recommendation: Dict[str, Any],
        technical_reasoning: str,
        standards_and_rfcs: List[str],
        record_id: Optional[str] = None,
    ):
        self.record_id = record_id or str(uuid4())
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.engine_name = engine_name
        self.input_conditions = input_conditions
        self.selected_recommendation = selected_recommendation
        self.technical_reasoning = technical_reasoning
        self.standards_and_rfcs = standards_and_rfcs

    def to_dict(self) -> Dict[str, Any]:
        """Convert explanation record to dictionary representation."""
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "engine_name": self.engine_name,
            "input_conditions": self.input_conditions,
            "selected_recommendation": self.selected_recommendation,
            "technical_reasoning": self.technical_reasoning,
            "standards_and_rfcs": self.standards_and_rfcs,
        }


class ExplainabilityEngine:
    """Engine dedicated to capturing and presenting architectural justification logs."""

    def __init__(self):
        self._history: List[ExplanationRecord] = []

    def record_explanation(
        self,
        engine_name: str,
        input_conditions: Dict[str, Any],
        selected_recommendation: Dict[str, Any],
        technical_reasoning: str,
        standards_and_rfcs: List[str]
    ) -> ExplanationRecord:
        """Records an explainability entry detailing why a recommendation was made.

        Args:
            engine_name: Name of the originating engine (e.g. 'MediaEngine', 'RoutingEngine').
            input_conditions: The input parameters and design constraints provided.
            selected_recommendation: The chosen option or architecture.
            technical_reasoning: Academic and technical justification.
            standards_and_rfcs: Applicable RFC or IEEE standard citations.

        Returns:
            The created ExplanationRecord instance.
        """
        record = ExplanationRecord(
            engine_name=engine_name,
            input_conditions=input_conditions,
            selected_recommendation=selected_recommendation,
            technical_reasoning=technical_reasoning,
            standards_and_rfcs=standards_and_rfcs,
        )
        self._history.append(record)
        return record

    def get_explanation(self, record_id: str) -> Optional[ExplanationRecord]:
        """Fetch a specific explanation by ID."""
        for record in self._history:
            if record.record_id == record_id:
                return record
        return None

    def list_explanations(self) -> List[Dict[str, Any]]:
        """Return all recorded explanation summaries in chronological order."""
        return [record.to_dict() for record in self._history]

    def clear(self) -> None:
        """Clear explanation history (primarily for test resets)."""
        self._history.clear()
