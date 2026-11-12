"""Health check endpoint route module."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="System Health Check")
def health_check():
    """Returns the operational status of the NetArchitect backend."""
    return {"status": "healthy"}
