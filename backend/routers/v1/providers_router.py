"""
NEXUS AI Provider Management & Execution REST API Router.
Mounted at /api/v1/providers with standard bearer auth.
"""

import time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from orchestrator.providers import (
    provider_router,
    usage_tracker,
    circuit_breaker
)
from models.schemas import (
    ProviderHealthResponse,
    ProviderMetadata,
    LLMGenerationRequest,
    LLMGenerationResponse
)

router = APIRouter(prefix="/providers", tags=["AI Providers"])


class ProviderSwitchRequest(BaseModel):
    provider_name: str


class CircuitResetRequest(BaseModel):
    provider_name: Optional[str] = None


@router.get("")
def list_providers():
    """Lists all registered providers with real-time health and capabilities."""
    return provider_router.list_providers()


@router.get("/health")
def get_providers_health():
    """Returns health and circuit breaker status across all providers."""
    health_map = {}
    for p_info in provider_router.list_providers():
        health_map[p_info["name"]] = p_info["health"]
    return {
        "providers": health_map,
        "default_preference": provider_router.default_preference
    }


@router.get("/usage")
def get_usage_metrics():
    """Returns persistent token usage, cost accounting, and invocation telemetry."""
    return usage_tracker.get_summary()


@router.post("/switch")
def switch_active_provider(req: ProviderSwitchRequest):
    """Sets the primary preferred AI provider."""
    prov = provider_router.get_provider(req.provider_name)
    if not prov:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{req.provider_name}'")
    provider_router.set_default_preference(req.provider_name)
    return {
        "status": "UPDATED",
        "active_provider": provider_router.default_preference
    }


@router.post("/generate", response_model=LLMGenerationResponse)
async def execute_generation(req: LLMGenerationRequest):
    """Executes resilient model generation with automatic fallback cascade and zero-cost guardrail."""
    try:
        return await provider_router.generate(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/reset-circuit")
def reset_provider_circuit(req: CircuitResetRequest):
    """Resets tripped circuit breaker for a provider or all providers."""
    if req.provider_name:
        circuit_breaker.reset(f"provider:{req.provider_name.lower().strip()}")
        return {"status": "RESET", "target": req.provider_name}
    circuit_breaker.reset()
    return {"status": "RESET", "target": "all"}
