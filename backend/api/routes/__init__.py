"""API routes package for NetArchitect."""

from fastapi import APIRouter
from api.routes import health, scenarios, media, subnetting, routing, configs

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(scenarios.router, prefix="/scenarios", tags=["Scenarios"])
api_router.include_router(media.router, prefix="/media", tags=["Physical Media"])
api_router.include_router(subnetting.router, prefix="/subnetting", tags=["Subnetting / VLSM"])
api_router.include_router(routing.router, prefix="/routing", tags=["Routing Protocols"])
api_router.include_router(configs.router, prefix="/configs", tags=["Configuration Generator"])
