
from fastapi import FastAPI

from backend.app.api.business import router as business_router
from backend.app.api.datasets import router as datasets_router
from backend.app.api.hazards import router as hazards_router
from backend.app.api.weather import router as weather_router
from backend.app.api.weather_features import (
    router as weather_features_router,
)

app = FastAPI(
    title="TerraCred API",
    description="Climate risk assessment for MSMEs",
    version="0.1.0",
)

# Register API routers
app.include_router(datasets_router)
app.include_router(weather_router)
app.include_router(weather_features_router)
app.include_router(hazards_router)
app.include_router(business_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to TerraCred API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "terracred-backend",
    }
