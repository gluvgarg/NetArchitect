"""NetArchitect Backend Application.

Algorithmic Network Planning, Recommendation, and Configuration Engine.
Academic Project for Computer Networks.
"""

import sys
from pathlib import Path

# Ensure backend directory is in sys.path for both root and local execution
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.routes import api_router
from engines.media_engine import PhysicalDistanceViolationError

app = FastAPI(
    title="NetArchitect API",
    description="Algorithmic Network Planning and Configuration Engine",
    version="1.0.0"
)

# Custom Exception Handler for Physical Distance Constraints
@app.exception_handler(PhysicalDistanceViolationError)
def physical_distance_violation_handler(request: Request, exc: PhysicalDistanceViolationError):
    return JSONResponse(
        status_code=400,
        content={
            "detail": {
                "error_type": "PhysicalDistanceViolationError",
                "message": exc.message,
                "requested_medium": exc.requested_medium,
                "distance_meters": exc.distance_meters,
                "max_distance_meters": exc.max_distance_meters,
                "attenuation_explanation": exc.attenuation_explanation,
            }
        },
    )

# CORS Configuration allowing React Vite frontend
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include modular API routers under /api/v1
app.include_router(api_router, prefix="/api/v1")


@app.get("/", summary="Root Status")
def home():
    """Welcome endpoint confirming backend status."""
    return {
        "message": "Welcome to NetArchitect!",
        "status": "Backend is running"
    }


@app.get("/health", summary="Top-Level Health Check")
def health_check():
    """Health check endpoint for frontend connectivity and monitoring."""
    return {"status": "healthy"}
