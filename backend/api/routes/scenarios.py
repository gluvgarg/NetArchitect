"""Network Scenario management routes.

Handles profiles for:
- Campus LAN
- Metro MAN
- Global WAN
"""

from fastapi import APIRouter
from services.scenario_service import scenario_service

router = APIRouter()


@router.get("/", summary="List Supported Network Profiles")
def list_scenarios():
    """Retrieve all standard network profiles supported by NetArchitect."""
    return {
        "status": "success",
        "profiles": scenario_service.list_profiles(),
    }


@router.get("/{profile_id}", summary="Get Network Profile Specification")
def get_scenario(profile_id: str):
    """Retrieve detailed constraints and specifications for a given profile."""
    profile = scenario_service.get_profile(profile_id)
    if not profile:
        return {"status": "error", "message": f"Profile '{profile_id}' not found"}
    return {"status": "success", "profile": profile}
