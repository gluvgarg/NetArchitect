"""Unit and Integration Tests for Routing Decision Engine (Phase 5).

Academic Context:
Validates deterministic routing architecture selection rules, autonomous system
boundaries (RFC 4271), OSPF area hierarchy (RFC 2328), scale thresholds,
precedence hierarchies, Pydantic validations, and explainability audit logs.
"""

import pytest
from pydantic import ValidationError
from fastapi import HTTPException

from engines.routing_engine import RoutingEngine
from engines.explainability_engine import ExplainabilityEngine
from models.routing import (
    RoutingRecommendationRequest,
    RoutingRecommendationResponse,
    AutonomousSystemInfo,
    OSPFAreaInfo,
)
from api.routes.routing import recommend_routing, routing_info


@pytest.fixture
def explainability_engine():
    """Provides a fresh ExplainabilityEngine fixture."""
    return ExplainabilityEngine()


@pytest.fixture
def engine(explainability_engine):
    """Provides a fresh RoutingEngine instance with an explainability engine."""
    return RoutingEngine(explainability_engine=explainability_engine)


# ==============================================================================
# 1. Single-Area OSPF (Area 0) Tests
# ==============================================================================

def test_single_as_20_subnets_recommends_single_area_ospf(engine):
    """Single AS with 20 subnets (< 50) and 1 site must recommend Single-Area OSPF Area 0."""
    result = engine.recommend_routing(
        network_name="Campus-LAN-Core",
        autonomous_system_count=1,
        subnet_count=20,
        site_count=1,
        has_external_as_boundary=False,
    )

    assert result["recommended_protocol"] == "Single-Area OSPF (Area 0)"
    assert result["architecture_type"] == "Interior Gateway Protocol (IGP) - Single-Area Link-State"
    assert result["area_0_required"] is True
    assert result["abr_required"] is False
    assert result["requires_design_review"] is False

    # AS Information
    assert result["autonomous_system_info"]["as_count"] == 1
    assert result["autonomous_system_info"]["is_multi_as"] is False
    assert result["autonomous_system_info"]["has_external_boundary"] is False

    # OSPF Area Information
    assert result["ospf_area_info"]["area_count"] == 1
    assert result["ospf_area_info"]["backbone_area"] == "Area 0 (0.0.0.0)"
    assert result["ospf_area_info"]["requires_area_0"] is True
    assert result["ospf_area_info"]["requires_abr"] is False

    # Academic reasoning and standards
    assert "Dijkstra" in result["reason_for_selection"]
    assert "Link-State Database" in result["reason_for_selection"] or "LSDB" in result["reason_for_selection"]
    assert any("RFC 2328" in std for std in result["standards_and_rfcs"])
    assert result["explainability_record_id"] is not None


def test_single_as_under_50_subnets_boundary_49(engine):
    """Boundary test: 49 subnets within 1 AS must cleanly recommend Single-Area OSPF."""
    result = engine.recommend_routing(
        network_name="Large-Department",
        autonomous_system_count=1,
        subnet_count=49,
        site_count=1,
        has_external_as_boundary=False,
    )

    assert result["recommended_protocol"] == "Single-Area OSPF (Area 0)"
    assert result["requires_design_review"] is False
    assert result["area_0_required"] is True
    assert result["abr_required"] is False


# ==============================================================================
# 2. Multi-Area OSPF Tests
# ==============================================================================

def test_single_as_with_explicit_multi_areas_recommends_multi_area_ospf(engine):
    """Single AS with multiple explicitly required internal areas must recommend Multi-Area OSPF."""
    result = engine.recommend_routing(
        network_name="Regional-Campus",
        autonomous_system_count=1,
        subnet_count=35,
        site_count=3,
        has_external_as_boundary=False,
        ospf_areas_required=4,
    )

    assert result["recommended_protocol"] == "Multi-Area OSPF"
    assert result["architecture_type"] == "Interior Gateway Protocol (IGP) - Hierarchical Link-State"
    assert result["area_0_required"] is True
    assert result["abr_required"] is True
    assert result["requires_design_review"] is False

    # OSPF Area hierarchy verification
    ospf_info = result["ospf_area_info"]
    assert ospf_info["area_count"] == 4
    assert ospf_info["backbone_area"] == "Area 0 (0.0.0.0)"
    assert ospf_info["requires_area_0"] is True
    assert ospf_info["requires_abr"] is True
    assert "Area 0 (0.0.0.0)" in ospf_info["area_roles"]
    assert "Area 1" in ospf_info["area_roles"]
    assert "Area 2" in ospf_info["area_roles"]
    assert "Area 3" in ospf_info["area_roles"]

    # Technical rationale mentions ABR and Area 0 backbone
    assert "Area Border Router" in result["reason_for_selection"] or "ABR" in result["reason_for_selection"]
    assert "backbone" in result["reason_for_selection"].lower()
    assert any("RFC 2328" in std for std in result["standards_and_rfcs"])


def test_multi_area_ospf_isolates_link_flaps(engine):
    """Multi-Area OSPF characteristics must explain SPF isolation across ABR boundaries."""
    result = engine.recommend_routing(
        network_name="Metro-Backbone",
        autonomous_system_count=1,
        subnet_count=80,
        site_count=4,
        has_external_as_boundary=False,
        ospf_areas_required=3,
    )

    assert any("Type 3" in char for char in result["routing_characteristics"])
    assert any("SPF" in adv for adv in result["advantages"])


# ==============================================================================
# 3. eBGP Tests
# ==============================================================================

def test_multiple_ases_recommends_ebgp(engine):
    """Multiple Autonomous Systems must recommend eBGP for inter-AS routing."""
    result = engine.recommend_routing(
        network_name="Inter-Domain-WAN",
        autonomous_system_count=3,
        subnet_count=40,
        site_count=5,
        has_external_as_boundary=True,
    )

    assert result["recommended_protocol"] == "eBGP (External Border Gateway Protocol)"
    assert result["architecture_type"] == "Exterior Gateway Protocol (EGP) - Inter-AS Path-Vector"
    assert result["area_0_required"] is False
    assert result["abr_required"] is False
    assert result["requires_design_review"] is False

    # Verify AS information
    assert result["autonomous_system_info"]["as_count"] == 3
    assert result["autonomous_system_info"]["is_multi_as"] is True
    assert result["autonomous_system_info"]["has_external_boundary"] is True

    # Critical requirement: eBGP does NOT replace internal routing protocol
    reason = result["reason_for_selection"]
    assert "AS_PATH" in reason
    assert "not replace" in reason.lower() or "does not replace" in reason.lower()
    assert "igp" in reason.lower() or "interior gateway protocol" in reason.lower()

    # Standards citation
    assert any("RFC 4271" in std for std in result["standards_and_rfcs"])


def test_explicit_external_as_boundary_recommends_ebgp_even_for_single_as(engine):
    """Enterprise with 1 internal AS peering across an external AS boundary must recommend eBGP."""
    result = engine.recommend_routing(
        network_name="Enterprise-ISP-Egress",
        autonomous_system_count=1,
        subnet_count=10,
        site_count=1,
        has_external_as_boundary=True,
    )

    assert result["recommended_protocol"] == "eBGP (External Border Gateway Protocol)"
    assert result["architecture_type"] == "Exterior Gateway Protocol (EGP) - Inter-AS Path-Vector"
    assert result["autonomous_system_info"]["has_external_boundary"] is True
    assert "AS_PATH" in result["reason_for_selection"]
    assert "does not replace" in result["reason_for_selection"].lower()


# ==============================================================================
# 4. Multi-Site Network Handling (Does NOT Automatically Require BGP)
# ==============================================================================

def test_multisite_network_without_external_boundary_does_not_use_bgp(engine):
    """Multi-site network within a single AS without external boundary must NOT default to BGP."""
    result = engine.recommend_routing(
        network_name="MultiBranch-Enterprise",
        autonomous_system_count=1,
        subnet_count=12,
        site_count=4,  # Multiple sites
        has_external_as_boundary=False,
    )

    # Must NOT recommend BGP
    assert "BGP" not in result["recommended_protocol"]
    assert result["recommended_protocol"] == "Single-Area OSPF (Area 0)"

    # Reason must explicitly mention that multi-site alone does not mandate BGP
    assert "multi-site" in result["reason_for_selection"].lower()
    assert "not mandate bgp" in result["reason_for_selection"].lower() or "does not require ebgp" in result["reason_for_selection"].lower()


def test_multisite_network_with_multiple_areas_recommends_multi_area_ospf(engine):
    """Multi-site network with explicit area partitioning uses Multi-Area OSPF without BGP."""
    result = engine.recommend_routing(
        network_name="MultiCampus-LAN",
        autonomous_system_count=1,
        subnet_count=30,
        site_count=3,
        has_external_as_boundary=False,
        ospf_areas_required=3,
    )

    assert result["recommended_protocol"] == "Multi-Area OSPF"
    assert "BGP" not in result["recommended_protocol"]


# ==============================================================================
# 5. Boundary Tests: Exactly 50 Subnets
# ==============================================================================

def test_exactly_50_subnets_without_area_count_requires_design_review(engine):
    """Exactly 50 subnets without explicit area count must trigger Design Review rather than guessing."""
    result = engine.recommend_routing(
        network_name="Threshold-Campus",
        autonomous_system_count=1,
        subnet_count=50,
        site_count=2,
        has_external_as_boundary=False,
        ospf_areas_required=None,
    )

    assert result["requires_design_review"] is True
    assert result["recommended_protocol"] == "Design Review Required: OSPF Area Partitioning"
    assert result["architecture_type"] == "Hierarchical IGP Planning"
    assert "50" in result["reason_for_selection"]
    assert "will not arbitrarily" in result["reason_for_selection"] or "cannot be guessed" in result["alternatives_rejected"] if "alternatives_rejected" in result else True


def test_exactly_50_subnets_with_explicit_areas_recommends_multi_area_ospf(engine):
    """50 subnets with explicit area specification cleanly resolves to Multi-Area OSPF."""
    result = engine.recommend_routing(
        network_name="Threshold-Campus-Planned",
        autonomous_system_count=1,
        subnet_count=50,
        site_count=2,
        has_external_as_boundary=False,
        ospf_areas_required=2,
    )

    assert result["requires_design_review"] is False
    assert result["recommended_protocol"] == "Multi-Area OSPF"


def test_50_subnets_with_explicit_single_area_returns_warning(engine):
    """50 subnets with explicit ospf_areas_required=1 honors request but flags scale limitation."""
    result = engine.recommend_routing(
        network_name="Explicit-Flat-Large-Net",
        autonomous_system_count=1,
        subnet_count=50,
        site_count=1,
        has_external_as_boundary=False,
        ospf_areas_required=1,
    )

    assert result["recommended_protocol"] == "Single-Area OSPF (Area 0)"
    assert any("50 subnets" in lim for lim in result["limitations"])


# ==============================================================================
# 6. Missing or Contradictory Topology Information Tests
# ==============================================================================

def test_contradictory_multi_as_without_external_boundary_requires_design_review(engine):
    """Multiple ASes with has_external_as_boundary=False is contradictory; returns design review."""
    result = engine.recommend_routing(
        network_name="Contradictory-Topology",
        autonomous_system_count=2,
        subnet_count=10,
        site_count=2,
        has_external_as_boundary=False,  # Contradiction: AS > 1 cannot lack external boundary
    )

    assert result["requires_design_review"] is True
    assert "Contradictory" in result["recommended_protocol"]
    assert "Contradictory topology parameters" in result["reason_for_selection"]
    assert result["autonomous_system_info"]["is_multi_as"] is True
    assert result["autonomous_system_info"]["has_external_boundary"] is False


# ==============================================================================
# 7. Decision Precedence Tests
# ==============================================================================

def test_precedence_external_boundary_overrides_small_subnet_count(engine):
    """External AS boundary takes precedence over small subnet count (< 50)."""
    result = engine.recommend_routing(
        network_name="Small-Net-With-Egress",
        autonomous_system_count=1,
        subnet_count=3,  # Very small subnet count
        site_count=1,
        has_external_as_boundary=True,  # External peering active
    )

    # eBGP must take precedence over Single-Area OSPF for the inter-domain boundary
    assert result["recommended_protocol"] == "eBGP (External Border Gateway Protocol)"
    assert result["area_0_required"] is False


def test_precedence_external_boundary_overrides_multi_area(engine):
    """External AS boundary takes precedence over internal multi-area requests for inter-AS routing."""
    result = engine.recommend_routing(
        network_name="Multi-Area-With-ISP",
        autonomous_system_count=2,
        subnet_count=40,
        site_count=2,
        has_external_as_boundary=True,
        ospf_areas_required=4,
    )

    # Rule 1 takes precedence
    assert result["recommended_protocol"] == "eBGP (External Border Gateway Protocol)"


def test_precedence_explicit_multi_area_overrides_small_subnet_count(engine):
    """Explicit ospf_areas_required > 1 overrides small subnet count (< 50)."""
    result = engine.recommend_routing(
        network_name="Small-Subnet-Multi-Area",
        autonomous_system_count=1,
        subnet_count=10,  # Under 50 subnets
        site_count=2,
        has_external_as_boundary=False,
        ospf_areas_required=2,  # Explicitly requires 2 areas
    )

    # Rule 2 takes precedence over Rule 3
    assert result["recommended_protocol"] == "Multi-Area OSPF"
    assert result["ospf_area_info"]["area_count"] == 2


# ==============================================================================
# 8. Engine Input Validation Tests (ValueErrors)
# ==============================================================================

def test_engine_zero_as_count_raises_value_error(engine):
    """Autonomous system count of 0 must raise ValueError."""
    with pytest.raises(ValueError, match="Autonomous system count must be a positive integer"):
        engine.recommend_routing(
            network_name="Test-Net",
            autonomous_system_count=0,
            subnet_count=10,
        )


def test_engine_negative_as_count_raises_value_error(engine):
    """Negative AS count must raise ValueError."""
    with pytest.raises(ValueError, match="Autonomous system count must be a positive integer"):
        engine.recommend_routing(
            network_name="Test-Net",
            autonomous_system_count=-2,
            subnet_count=10,
        )


def test_engine_zero_subnet_count_raises_value_error(engine):
    """Subnet count of 0 must raise ValueError."""
    with pytest.raises(ValueError, match="Subnet count must be a positive integer"):
        engine.recommend_routing(
            network_name="Test-Net",
            autonomous_system_count=1,
            subnet_count=0,
        )


def test_engine_negative_subnet_count_raises_value_error(engine):
    """Negative subnet count must raise ValueError."""
    with pytest.raises(ValueError, match="Subnet count must be a positive integer"):
        engine.recommend_routing(
            network_name="Test-Net",
            autonomous_system_count=1,
            subnet_count=-5,
        )


def test_engine_zero_ospf_area_count_raises_value_error(engine):
    """OSPF area count of 0 must raise ValueError."""
    with pytest.raises(ValueError, match="OSPF area count must be a positive integer"):
        engine.recommend_routing(
            network_name="Test-Net",
            autonomous_system_count=1,
            subnet_count=10,
            ospf_areas_required=0,
        )


def test_engine_negative_ospf_area_count_raises_value_error(engine):
    """Negative OSPF area count must raise ValueError."""
    with pytest.raises(ValueError, match="OSPF area count must be a positive integer"):
        engine.recommend_routing(
            network_name="Test-Net",
            autonomous_system_count=1,
            subnet_count=10,
            ospf_areas_required=-3,
        )


def test_engine_zero_site_count_raises_value_error(engine):
    """Site count of 0 must raise ValueError."""
    with pytest.raises(ValueError, match="Site count must be a positive integer"):
        engine.recommend_routing(
            network_name="Test-Net",
            autonomous_system_count=1,
            subnet_count=10,
            site_count=0,
        )


def test_engine_empty_network_name_raises_value_error(engine):
    """Empty or whitespace network name must raise ValueError."""
    with pytest.raises(ValueError, match="Network name must be a non-empty string"):
        engine.recommend_routing(
            network_name="   ",
            autonomous_system_count=1,
            subnet_count=10,
        )


# ==============================================================================
# 9. Pydantic Model Validation Tests
# ==============================================================================

def test_pydantic_routing_request_valid():
    """Valid RoutingRecommendationRequest model instantiation."""
    req = RoutingRecommendationRequest(
        network_name="Core-Backbone",
        autonomous_system_count=1,
        subnet_count=24,
        site_count=2,
        has_external_as_boundary=False,
        ospf_areas_required=2,
    )
    assert req.network_name == "Core-Backbone"
    assert req.autonomous_system_count == 1
    assert req.subnet_count == 24
    assert req.ospf_areas_required == 2


def test_pydantic_routing_request_rejects_empty_name():
    """Pydantic model rejects empty network name."""
    with pytest.raises(ValidationError):
        RoutingRecommendationRequest(
            network_name="   ",
            subnet_count=10,
        )


def test_pydantic_routing_request_rejects_zero_as():
    """Pydantic model rejects AS count < 1."""
    with pytest.raises(ValidationError):
        RoutingRecommendationRequest(
            network_name="Test-Net",
            autonomous_system_count=0,
            subnet_count=10,
        )


def test_pydantic_routing_request_rejects_zero_subnets():
    """Pydantic model rejects subnet count < 1."""
    with pytest.raises(ValidationError):
        RoutingRecommendationRequest(
            network_name="Test-Net",
            subnet_count=0,
        )


def test_pydantic_routing_request_rejects_zero_areas():
    """Pydantic model rejects OSPF area count < 1."""
    with pytest.raises(ValidationError):
        RoutingRecommendationRequest(
            network_name="Test-Net",
            subnet_count=10,
            ospf_areas_required=0,
        )


# ==============================================================================
# 10. Explainability Audit Logging Tests
# ==============================================================================

def test_routing_explainability_audit_logging(engine):
    """Explainability record is logged with RFC standards, rule, and conditions."""
    result = engine.recommend_routing(
        network_name="Audit-Exam-Network",
        autonomous_system_count=1,
        subnet_count=15,
        site_count=1,
        has_external_as_boundary=False,
    )

    record_id = result["explainability_record_id"]
    assert record_id is not None

    record = engine.explainability_engine.get_explanation(record_id)
    assert record is not None
    assert record.engine_name == "RoutingEngine"
    assert "RFC 2328" in record.standards_and_rfcs[0]
    assert record.input_conditions["network_name"] == "Audit-Exam-Network"
    assert record.input_conditions["subnet_count"] == 15
    assert record.selected_recommendation["recommended_protocol"] == "Single-Area OSPF (Area 0)"


# ==============================================================================
# 11. API Route Endpoint Integration Tests
# ==============================================================================

def test_api_route_info_endpoint():
    """GET / endpoint returns 200 and operational metadata."""
    info = routing_info()
    assert info["status"] == "ready"
    assert len(info["supported_architectures"]) == 3
    assert info["scalability_thresholds"]["single_area_max_subnets"] == 50


def test_api_route_successful_single_area_ospf():
    """POST /recommend endpoint returns 200 OK and valid Single-Area OSPF response."""
    req = RoutingRecommendationRequest(
        network_name="Campus-Core",
        autonomous_system_count=1,
        subnet_count=15,
        site_count=1,
        has_external_as_boundary=False,
    )
    resp = recommend_routing(req)

    assert resp["network_name"] == "Campus-Core"
    assert resp["recommended_protocol"] == "Single-Area OSPF (Area 0)"
    assert resp["area_0_required"] is True
    assert resp["abr_required"] is False
    assert resp["requires_design_review"] is False


def test_api_route_successful_multi_area_ospf():
    """POST /recommend endpoint returns 200 OK and valid Multi-Area OSPF response."""
    req = RoutingRecommendationRequest(
        network_name="Regional-LAN",
        autonomous_system_count=1,
        subnet_count=60,
        site_count=3,
        has_external_as_boundary=False,
        ospf_areas_required=3,
    )
    resp = recommend_routing(req)

    assert resp["recommended_protocol"] == "Multi-Area OSPF"
    assert resp["area_0_required"] is True
    assert resp["abr_required"] is True


def test_api_route_successful_ebgp():
    """POST /recommend endpoint returns 200 OK and valid eBGP response."""
    req = RoutingRecommendationRequest(
        network_name="Global-Core",
        autonomous_system_count=2,
        subnet_count=20,
        site_count=3,
        has_external_as_boundary=True,
    )
    resp = recommend_routing(req)

    assert resp["recommended_protocol"] == "eBGP (External Border Gateway Protocol)"
    assert resp["area_0_required"] is False
    assert "AS_PATH" in resp["reason_for_selection"]


def test_api_route_validation_error_raises_http_422():
    """Engine ValueError inside recommend_routing must translate to HTTP 422."""
    # Create request with valid model, then inject an invalid parameter that the engine catches
    req = RoutingRecommendationRequest(
        network_name="Test-Net",
        autonomous_system_count=1,
        subnet_count=10,
    )
    # Manually overwrite field to simulate an edge-case engine ValueError
    req.network_name = ""  # Will trigger engine ValueError

    with pytest.raises(HTTPException) as exc_info:
        recommend_routing(req)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error_type"] == "ValidationError"
