"""Comprehensive unit tests for the Physical Media Recommendation Engine.

Covers:
- Distance-based selection tiers:
  * <= 100m: Cat6a Copper (10GBASE-T, IEEE 802.3an)
  * 101m - 400m: OM4 Multimode Fiber (10GBASE-SR, 850 nm, IEEE 802.3ae)
  * 401m - 10,000m: OS2 Single-Mode Fiber (10GBASE-LR, 1310 nm, IEEE 802.3ae)
  * 10,001m - 40,000m: OS2 Single-Mode Fiber Extended (10GBASE-ER, 1550 nm, IEEE 802.3ae)
  * > 40,000m: PhysicalDistanceViolationError (exceeds unamplified point-to-point reach)
- Exact boundary tests:
  * 100m vs 101m
  * 400m vs 401m
  * 10,000m vs 10,001m
  * 40,000m vs 40,001m
- Preferred-medium policy matrix:
  * Preferred copper at 100m -> allowed (Cat6a)
  * Preferred copper at 101m -> PhysicalDistanceViolationError
  * Preferred copper at 250m -> PhysicalDistanceViolationError
  * Preferred OM4 at 75m -> honored (OM4 MMF with EMI explanation)
  * Preferred OS2 at 250m -> honored (OS2 SMF with future-proofing explanation)
  * Preferred multimode at 401m -> PhysicalDistanceViolationError
- Optical power budget analysis & distinction:
  * Standardized reach vs estimated installation loss vs budget sufficiency
  * 850m (LR) -> +1.86 dB margin -> is_budget_sufficient: True
  * 10,000m (LR) -> -1.80 dB margin -> is_budget_sufficient: False
  * 10,001m (ER) -> +4.60 dB margin -> is_budget_sufficient: True
  * 40,000m (ER) -> -2.90 dB margin -> is_budget_sufficient: False
  * Link engineering recommendations generated when margin is negative
- Cat6a numerical attenuation specification accuracy (49.3 dB at 500 MHz, ANSI/TIA-568-C.2)
- Input validation (zero, negative, unrecognized preferred medium)
- Explainability engine integration and audit logging
- API route endpoints and error status codes
"""

import sys
from pathlib import Path
import pytest
from pydantic import ValidationError
from fastapi import HTTPException

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from engines.media_engine import MediaEngine, PhysicalDistanceViolationError
from engines.explainability_engine import ExplainabilityEngine
from models.media import MediaRecommendationRequest, MediaRecommendationResponse
from api.routes.media import recommend_media


@pytest.fixture
def engine():
    """Provides a fresh MediaEngine instance with isolated ExplainabilityEngine."""
    exp_engine = ExplainabilityEngine()
    return MediaEngine(explainability_engine=exp_engine)


# ==============================================================================
# 1. Distance-Based Selection Tests & Boundaries
# ==============================================================================

def test_distance_75m_selects_cat6a(engine):
    """Distance: 75 m -> Cat6a copper, 10GBASE-T, IEEE 802.3an."""
    result = engine.recommend_media(distance_meters=75.0)
    assert "Cat6a" in result["selected_medium"]
    assert "10GBASE-T" in result["technology_standard"]
    assert "IEEE 802.3an" in result["technology_standard"]
    assert result["max_supported_distance_meters"] == 100.0
    assert result["wavelength_nm"] is None
    assert "49.3 dB" in result["attenuation_rating"]
    assert "OM4 Multimode Fiber" in result["why_alternatives_not_selected"]
    assert "OS2 Single-mode Fiber" in result["why_alternatives_not_selected"]


def test_distance_100m_boundary_selects_cat6a(engine):
    """Distance: 100 m (boundary) -> Cat6a copper, 10GBASE-T, IEEE 802.3an."""
    result = engine.recommend_media(distance_meters=100.0)
    assert "Cat6a" in result["selected_medium"]
    assert "10GBASE-T" in result["technology_standard"]
    assert result["max_supported_distance_meters"] == 100.0


def test_distance_101m_boundary_selects_om4(engine):
    """Distance: 101 m (boundary) -> OM4 multimode fiber, 10GBASE-SR, 850 nm."""
    result = engine.recommend_media(distance_meters=101.0)
    assert "OM4" in result["selected_medium"]
    assert "10GBASE-SR" in result["technology_standard"]
    assert result["wavelength_nm"] == 850
    assert result["max_supported_distance_meters"] == 400.0
    assert "850 nm" in result["technical_reasoning"]
    assert "4700 MHz" in result["technical_reasoning"]
    assert "Cat6a" in list(result["why_alternatives_not_selected"].keys())[0]


def test_distance_250m_selects_om4(engine):
    """Distance: 250 m -> OM4 multimode fiber, 10GBASE-SR, 850 nm."""
    result = engine.recommend_media(distance_meters=250.0)
    assert "OM4" in result["selected_medium"]
    assert "10GBASE-SR" in result["technology_standard"]
    assert result["wavelength_nm"] == 850
    assert result["max_supported_distance_meters"] == 400.0
    assert "modal dispersion" in result["technical_reasoning"].lower()


def test_distance_400m_boundary_selects_om4(engine):
    """Distance: 400 m (boundary) -> OM4 multimode fiber, 10GBASE-SR, 850 nm."""
    result = engine.recommend_media(distance_meters=400.0)
    assert "OM4" in result["selected_medium"]
    assert "10GBASE-SR" in result["technology_standard"]
    assert result["wavelength_nm"] == 850
    assert result["max_supported_distance_meters"] == 400.0


def test_distance_401m_boundary_selects_os2_10gbase_lr(engine):
    """Distance: 401 m (boundary) -> OS2 single-mode fiber with 10GBASE-LR."""
    result = engine.recommend_media(distance_meters=401.0)
    assert "OS2" in result["selected_medium"]
    assert "10GBASE-LR" in result["technology_standard"]
    assert result["wavelength_nm"] == 1310
    assert result["max_supported_distance_meters"] == 10000.0
    assert result["optical_budget"] is not None
    assert result["optical_budget"]["power_budget_db"] == 6.2
    assert result["optical_budget"]["is_budget_sufficient"] is True


def test_distance_850m_selects_os2_10gbase_lr(engine):
    """Distance: 850 m -> OS2 single-mode fiber with 10GBASE-LR optical budget."""
    result = engine.recommend_media(distance_meters=850.0)
    assert "OS2" in result["selected_medium"]
    assert "10GBASE-LR" in result["technology_standard"]
    assert result["wavelength_nm"] == 1310
    assert result["optical_budget"] is not None
    assert result["optical_budget"]["fiber_loss_db"] == round(0.4 * 0.85, 3)
    assert result["optical_budget"]["is_budget_sufficient"] is True


# ==============================================================================
# 2. Detailed Optical Power Budget Validation & Distinction Tests
# ==============================================================================

def test_optical_budget_lr_850m_detailed_calculation(engine):
    """Detailed calculation for 10GBASE-LR at 850 m:
    - Distance: 0.85 km
    - Fiber loss: 0.4 dB/km * 0.85 km = 0.34 dB
    - Connector loss: 1.0 dB
    - Safety margin: 3.0 dB
    - Total estimated loss: 0.34 + 1.0 + 3.0 = 4.34 dB
    - Power margin: 6.2 - 4.34 = +1.86 dB
    - is_budget_sufficient: True
    - budget_status: 'sufficient'
    """
    result = engine.recommend_media(distance_meters=850.0)
    budget = result["optical_budget"]

    assert budget["power_budget_db"] == 6.2
    assert budget["fiber_loss_db"] == 0.34
    assert budget["connector_loss_db"] == 1.0
    assert budget["safety_margin_db"] == 3.0
    assert budget["total_estimated_loss_db"] == 4.34
    assert budget["power_margin_db"] == 1.86
    assert budget["is_budget_sufficient"] is True
    assert budget["budget_status"] == "sufficient"


def test_optical_budget_lr_10000m_insufficient_margin_detection(engine):
    """Detailed calculation for 10GBASE-LR at exactly 10,000 m (10 km):
    - Distance: 10.0 km
    - Standardized reach: 10,000 m (IEEE 802.3ae compliant)
    - Fiber loss: 0.4 dB/km * 10.0 km = 4.0 dB
    - Connector loss: 1.0 dB
    - Safety margin: 3.0 dB
    - Total estimated loss: 4.0 + 1.0 + 3.0 = 8.0 dB
    - Power margin: 6.2 - 8.0 = -1.8 dB (negative deficit!)
    - is_budget_sufficient: MUST BE FALSE (do not return True)
    - budget_status: 'insufficient_under_conservative_assumptions'
    - max_supported_distance_meters: MUST REMAIN 10,000 m (standard reach preserved)
    - engineering_recommendation: must provide optimization advice
    """
    result = engine.recommend_media(distance_meters=10000.0)
    budget = result["optical_budget"]

    assert result["max_supported_distance_meters"] == 10000.0  # Standard reach kept intact
    assert budget["power_budget_db"] == 6.2
    assert budget["fiber_loss_db"] == 4.0
    assert budget["connector_loss_db"] == 1.0
    assert budget["safety_margin_db"] == 3.0
    assert budget["total_estimated_loss_db"] == 8.0
    assert budget["power_margin_db"] == -1.8
    assert budget["is_budget_sufficient"] is False  # Correctly identifies insufficient margin
    assert budget["budget_status"] == "insufficient_under_conservative_assumptions"
    assert budget["engineering_recommendation"] is not None
    assert "link engineering" in budget["engineering_recommendation"].lower()
    assert "fusion splices" in budget["engineering_recommendation"].lower()


def test_optical_budget_er_10001m_detailed_calculation(engine):
    """Detailed calculation for 10GBASE-ER at 10,001 m:
    - Distance: 10.001 km
    - Fiber loss: 0.25 dB/km * 10.001 km = 2.50 dB
    - Connector loss: 1.0 dB
    - Safety margin: 3.0 dB
    - Total estimated loss: 2.50 + 1.0 + 3.0 = 6.50 dB
    - Power margin: 11.1 - 6.50 = +4.60 dB
    - is_budget_sufficient: True
    - budget_status: 'sufficient'
    """
    result = engine.recommend_media(distance_meters=10001.0)
    budget = result["optical_budget"]

    assert result["max_supported_distance_meters"] == 40000.0
    assert "10GBASE-ER" in result["technology_standard"]
    assert budget["power_budget_db"] == 11.1
    assert budget["fiber_loss_db"] == 2.50
    assert budget["connector_loss_db"] == 1.0
    assert budget["safety_margin_db"] == 3.0
    assert budget["total_estimated_loss_db"] == 6.50
    assert budget["power_margin_db"] == 4.60
    assert budget["is_budget_sufficient"] is True
    assert budget["budget_status"] == "sufficient"


def test_optical_budget_er_40000m_insufficient_margin_detection(engine):
    """Detailed calculation for 10GBASE-ER at exactly 40,000 m (40 km):
    - Distance: 40.0 km
    - Standardized reach: 40,000 m (IEEE 802.3ae compliant)
    - Fiber loss: 0.25 dB/km * 40.0 km = 10.0 dB
    - Connector loss: 1.0 dB
    - Safety margin: 3.0 dB
    - Total estimated loss: 10.0 + 1.0 + 3.0 = 14.0 dB
    - Power margin: 11.1 - 14.0 = -2.9 dB (negative deficit!)
    - is_budget_sufficient: MUST BE FALSE (do not return True)
    - budget_status: 'insufficient_under_conservative_assumptions'
    - max_supported_distance_meters: MUST REMAIN 40,000 m (standard reach preserved)
    - engineering_recommendation: must provide optimization advice
    """
    result = engine.recommend_media(distance_meters=40000.0)
    budget = result["optical_budget"]

    assert result["max_supported_distance_meters"] == 40000.0  # Standard reach kept intact
    assert budget["power_budget_db"] == 11.1
    assert budget["fiber_loss_db"] == 10.0
    assert budget["connector_loss_db"] == 1.0
    assert budget["safety_margin_db"] == 3.0
    assert budget["total_estimated_loss_db"] == 14.0
    assert budget["power_margin_db"] == -2.9
    assert budget["is_budget_sufficient"] is False  # Correctly identifies insufficient margin
    assert budget["budget_status"] == "insufficient_under_conservative_assumptions"
    assert budget["engineering_recommendation"] is not None
    assert "link engineering" in budget["engineering_recommendation"].lower()
    assert "0.20 db/km" in budget["engineering_recommendation"].lower() or "fusion" in budget["engineering_recommendation"].lower()


def test_distance_40001m_raises_unsupported_distance_violation(engine):
    """Distance: 40,001 m (> 40 km) -> Must raise PhysicalDistanceViolationError."""
    with pytest.raises(PhysicalDistanceViolationError) as exc_info:
        engine.recommend_media(distance_meters=40001.0)

    err = exc_info.value
    assert err.distance_meters == 40001.0
    assert err.max_distance_meters == 40000.0
    assert "40 km" in err.message
    assert "EDFA" in err.message or "unamplified" in err.message


# ==============================================================================
# 3. Preferred-Medium Policy Tests
# ==============================================================================

def test_preferred_copper_at_100m_allowed(engine):
    """Preferred copper at 100 m -> Allowed (Cat6a copper)."""
    result = engine.recommend_media(distance_meters=100.0, preferred_medium="copper")
    assert "Cat6a" in result["selected_medium"]
    assert result["requested_medium"] == "copper"


def test_preferred_copper_at_101m_raises_physical_distance_violation(engine):
    """Preferred copper at 101 m -> PhysicalDistanceViolationError (never silent replacement)."""
    with pytest.raises(PhysicalDistanceViolationError) as exc_info:
        engine.recommend_media(distance_meters=101.0, preferred_medium="copper")

    err = exc_info.value
    assert err.requested_medium == "copper"
    assert err.distance_meters == 101.0
    assert err.max_distance_meters == 100.0
    assert "attenuation" in err.attenuation_explanation.lower()
    assert "49.3 dB" in err.attenuation_explanation


def test_preferred_copper_at_250m_raises_physical_distance_violation(engine):
    """Preferred copper at 250 m -> PhysicalDistanceViolationError (never silent replacement)."""
    with pytest.raises(PhysicalDistanceViolationError) as exc_info:
        engine.recommend_media(distance_meters=250.0, preferred_medium="copper")

    err = exc_info.value
    assert err.requested_medium == "copper"
    assert err.distance_meters == 250.0
    assert err.max_distance_meters == 100.0


def test_preferred_om4_at_75m_honored(engine):
    """Preferred OM4 at 75 m -> Honored (OM4 multimode fiber with EMI explanation)."""
    result = engine.recommend_media(distance_meters=75.0, preferred_medium="multimode_fiber")
    assert "OM4" in result["selected_medium"]
    assert "10GBASE-SR" in result["technology_standard"]
    assert result["wavelength_nm"] == 850
    assert result["requested_medium"] == "multimode_fiber"
    assert "explicit preference" in result["technical_reasoning"].lower()


def test_preferred_os2_at_250m_honored(engine):
    """Preferred OS2 at 250 m -> Honored (OS2 single-mode fiber with future-proofing explanation)."""
    result = engine.recommend_media(distance_meters=250.0, preferred_medium="singlemode_fiber")
    assert "OS2" in result["selected_medium"]
    assert "10GBASE-LR" in result["technology_standard"]
    assert result["wavelength_nm"] == 1310
    assert result["requested_medium"] == "singlemode_fiber"
    assert result["optical_budget"] is not None
    assert "explicit preference" in result["technical_reasoning"].lower()


def test_preferred_multimode_at_401m_raises_physical_distance_violation(engine):
    """Preferred multimode at 401 m -> PhysicalDistanceViolationError (never silent replacement)."""
    with pytest.raises(PhysicalDistanceViolationError) as exc_info:
        engine.recommend_media(distance_meters=401.0, preferred_medium="multimode_fiber")

    err = exc_info.value
    assert "multimode" in err.requested_medium.lower()
    assert err.distance_meters == 401.0
    assert err.max_distance_meters == 400.0
    assert "modal dispersion" in err.attenuation_explanation.lower()


def test_preferred_copper_at_10001m_raises_physical_distance_violation(engine):
    """Preferred copper at 10,001 m -> PhysicalDistanceViolationError."""
    with pytest.raises(PhysicalDistanceViolationError) as exc_info:
        engine.recommend_media(distance_meters=10001.0, preferred_medium="copper")

    err = exc_info.value
    assert err.requested_medium == "copper"


# ==============================================================================
# 4. Technical Accuracy & Standards Citation Tests
# ==============================================================================

def test_cat6a_attenuation_specification_accuracy(engine):
    """Cat6a specification must cite ANSI/TIA-568-C.2 maximum channel insertion loss of 49.3 dB at 500 MHz."""
    result = engine.recommend_media(distance_meters=75.0)
    assert "49.3 dB" in result["attenuation_rating"]
    assert "500 MHz" in result["attenuation_rating"]
    assert "49.3 dB" in result["technical_reasoning"]
    assert "ANSI/TIA-568-C.2" in result["standards_and_rfcs"][1]


def test_optical_power_budget_specification_distinction(engine):
    """Optical power budget must distinguish standard transceiver parameters from installation estimates."""
    result = engine.recommend_media(distance_meters=850.0)
    budget = result["optical_budget"]
    # Standard specs (IEEE 802.3ae Clause 52)
    assert budget["tx_power_min_dbm"] == -8.2
    assert budget["rx_sensitivity_dbm"] == -14.4
    assert budget["power_budget_db"] == 6.2
    # Engineering estimates (ITU-T G.652.D / TIA-568-C.3)
    assert budget["attenuation_coefficient_db_per_km"] == 0.4
    assert budget["connector_loss_db"] == 1.0
    assert budget["safety_margin_db"] == 3.0


# ==============================================================================
# 5. Input Validation Tests (Zero, Negative, Invalid Preferred Medium)
# ==============================================================================

def test_engine_zero_distance_raises_value_error(engine):
    """Distance = 0 in engine -> ValueError."""
    with pytest.raises(ValueError, match="Distance must be positive"):
        engine.recommend_media(distance_meters=0.0)


def test_engine_negative_distance_raises_value_error(engine):
    """Distance = -50 in engine -> ValueError."""
    with pytest.raises(ValueError, match="Distance must be positive"):
        engine.recommend_media(distance_meters=-50.0)


def test_engine_invalid_preferred_medium_raises_value_error(engine):
    """Invalid preferred medium string -> ValueError."""
    with pytest.raises(ValueError, match="Invalid preferred_medium"):
        engine.recommend_media(distance_meters=75.0, preferred_medium="quantum_cable")


def test_model_zero_distance_raises_validation_error():
    """Pydantic model rejects zero distance."""
    with pytest.raises(ValidationError):
        MediaRecommendationRequest(distance_meters=0.0)


def test_model_negative_distance_raises_validation_error():
    """Pydantic model rejects negative distance."""
    with pytest.raises(ValidationError):
        MediaRecommendationRequest(distance_meters=-10.0)


def test_model_invalid_preferred_medium_raises_validation_error():
    """Pydantic model rejects invalid preferred medium."""
    with pytest.raises(ValidationError):
        MediaRecommendationRequest(distance_meters=50.0, preferred_medium="wireless_laser")


# ==============================================================================
# 6. Explainability Engine Integration Tests
# ==============================================================================

def test_explainability_engine_audit_record_created(engine):
    """Recommendation must create an explanation record with all details."""
    result = engine.recommend_media(distance_meters=250.0)
    record_id = result["explanation_record_id"]
    assert record_id is not None

    record = engine.explainability_engine.get_explanation(record_id)
    assert record is not None
    assert record.engine_name == "MediaEngine"
    assert record.input_conditions["distance_meters"] == 250.0
    assert "10GBASE-SR" in record.selected_recommendation["technology_standard"]
    assert len(record.standards_and_rfcs) > 0
    assert "IEEE 802.3ae" in record.standards_and_rfcs[0]


# ==============================================================================
# 7. API Route Endpoint Integration Tests
# ==============================================================================

def test_api_route_successful_recommendation():
    """POST /recommend endpoint returns 200 and valid schema."""
    req = MediaRecommendationRequest(distance_meters=75.0)
    response = recommend_media(req)
    assert "Cat6a" in response["selected_medium"]
    assert response["input_distance_meters"] == 75.0
    assert response["technology_standard"] == "10GBASE-T (IEEE 802.3an)"


def test_api_route_copper_at_101m_raises_http_400():
    """POST /recommend endpoint raises HTTP 400 for copper at 101 m."""
    req = MediaRecommendationRequest(distance_meters=101.0, preferred_medium="copper")
    with pytest.raises(HTTPException) as exc_info:
        recommend_media(req)

    assert exc_info.value.status_code == 400
    detail = exc_info.value.detail
    assert detail["error_type"] == "PhysicalDistanceViolationError"
    assert detail["distance_meters"] == 101.0
    assert detail["max_distance_meters"] == 100.0
    assert "attenuation" in detail["attenuation_explanation"].lower()


def test_api_route_os2_at_500m_returns_optical_budget():
    """POST /recommend endpoint returns optical budget for distance > 400 m."""
    req = MediaRecommendationRequest(distance_meters=500.0)
    response = recommend_media(req)
    assert "OS2" in response["selected_medium"]
    assert response["optical_budget"] is not None
    assert response["optical_budget"]["power_budget_db"] == 6.2
    assert response["optical_budget"]["is_budget_sufficient"] is True


def test_api_route_10001m_returns_10gbase_er():
    """POST /recommend endpoint returns 10GBASE-ER for 10,001 m."""
    req = MediaRecommendationRequest(distance_meters=10001.0)
    response = recommend_media(req)
    assert "10GBASE-ER" in response["technology_standard"]
    assert response["wavelength_nm"] == 1550
    assert response["optical_budget"]["power_budget_db"] == 11.1
    assert response["optical_budget"]["is_budget_sufficient"] is True


def test_api_route_os2_10000m_returns_insufficient_budget_flag():
    """POST /recommend for 10,000 m returns 200 with is_budget_sufficient: False."""
    req = MediaRecommendationRequest(distance_meters=10000.0)
    response = recommend_media(req)
    assert response["max_supported_distance_meters"] == 10000.0
    budget = response["optical_budget"]
    assert budget["is_budget_sufficient"] is False
    assert budget["power_margin_db"] == -1.8
    assert budget["budget_status"] == "insufficient_under_conservative_assumptions"
    assert budget["engineering_recommendation"] is not None


def test_api_route_os2_40000m_returns_insufficient_budget_flag():
    """POST /recommend for 40,000 m returns 200 with is_budget_sufficient: False."""
    req = MediaRecommendationRequest(distance_meters=40000.0)
    response = recommend_media(req)
    assert response["max_supported_distance_meters"] == 40000.0
    budget = response["optical_budget"]
    assert budget["is_budget_sufficient"] is False
    assert budget["power_margin_db"] == -2.9
    assert budget["budget_status"] == "insufficient_under_conservative_assumptions"
    assert budget["engineering_recommendation"] is not None
