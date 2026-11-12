"""Unit tests for root and health check endpoints and CORS configuration."""

from main import home, health_check, app
from services.scenario_service import scenario_service
from engines.explainability_engine import ExplainabilityEngine


def test_root_endpoint():
    """Verify that root endpoint preserves the expected welcome message."""
    response = home()
    assert response == {
        "message": "Welcome to NetArchitect!",
        "status": "Backend is running"
    }


def test_health_check_endpoint():
    """Verify that health check endpoint returns 'healthy'."""
    response = health_check()
    assert response == {"status": "healthy"}


def test_cors_configuration():
    """Verify that CORS middleware is registered with the expected origins."""
    middleware_found = False
    for middleware in app.user_middleware:
        allow_origins = middleware.kwargs.get("allow_origins", [])
        if "http://localhost:5173" in allow_origins and "http://127.0.0.1:5173" in allow_origins:
            middleware_found = True
            break
    assert middleware_found, "CORS middleware with frontend origins was not registered"


def test_api_routes_registered():
    """Verify all required API route modules are mounted and available in OpenAPI schema."""
    paths = list(app.openapi().get("paths", {}).keys())
    assert "/" in paths
    assert "/health" in paths
    assert "/api/v1/health" in paths
    assert "/api/v1/scenarios/" in paths
    assert "/api/v1/media/" in paths
    assert "/api/v1/subnetting/" in paths
    assert "/api/v1/routing/" in paths
    assert "/api/v1/configs/" in paths


def test_scenario_service_mandatory_profiles():
    """Verify that the 3 mandatory network profiles are properly managed."""
    profiles = scenario_service.list_profiles()
    profile_ids = [p["id"] for p in profiles]
    assert "campus_lan" in profile_ids
    assert "metro_man" in profile_ids
    assert "global_wan" in profile_ids

    # Validate individual profile details
    lan = scenario_service.get_profile("campus_lan")
    assert lan is not None
    assert lan["name"] == "Campus LAN"

    man = scenario_service.get_profile("metro_man")
    assert man is not None
    assert man["name"] == "Metro MAN"

    wan = scenario_service.get_profile("global_wan")
    assert wan is not None
    assert wan["name"] == "Global WAN"


def test_explainability_engine_scaffolding():
    """Verify explainability engine records input, recommendations, reasoning, and standards."""
    engine = ExplainabilityEngine()
    record = engine.record_explanation(
        engine_name="MediaEngine",
        input_conditions={"distance_meters": 75, "bandwidth_mbps": 1000},
        selected_recommendation={"media": "Cat6 UTP"},
        technical_reasoning="Cat6 supports up to 10 Gbps over 55m and 1 Gbps up to 100m, satisfying the 75m requirement.",
        standards_and_rfcs=["IEEE 802.3ab (1000BASE-T)", "TIA-568.2-D"]
    )
    assert record.record_id is not None
    assert record.engine_name == "MediaEngine"
    assert "IEEE 802.3ab (1000BASE-T)" in record.standards_and_rfcs

    fetched = engine.get_explanation(record.record_id)
    assert fetched is not None
    assert fetched.record_id == record.record_id
    assert len(engine.list_explanations()) == 1
