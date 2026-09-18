"""
NEXUS Phase 21: Autonomous Software Factory & Product Builder API Router.

Exposes REST endpoints for:
- Product Blueprint & PRD Synthesis (/synthesize)
- Autonomous End-to-End Product Build & Execution (/build)
- Build Run Inspections & In-Flight Diagnostics (/builds, /builds/{build_id})
- Self-Correction / Repair Triggers (/builds/{build_id}/repair)
- Product Specifications (/specs, /specs/{spec_id})
- Product Catalog & Delivery Registry (/catalog)
- Builder Telemetry & FinOps Zero-Cost Health (/telemetry, /health)
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, status

from models.schemas import (
    ProductSpecification,
    ProductBuildRun,
    ProductSynthesizeRequest,
    ProductBuildRequest,
    ProductBuilderTelemetry
)
from orchestrator.product_builder_engine import product_builder_engine

router = APIRouter(prefix="", tags=["Phase 21 - Product Builder"])


@router.post("/product-builder/synthesize", response_model=ProductSpecification, status_code=status.HTTP_201_CREATED)
def synthesize_blueprint(req: ProductSynthesizeRequest):
    """Synthesizes a structured PRD / Product Blueprint from high-level natural language."""
    try:
        return product_builder_engine.synthesize_product_blueprint(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/product-builder/build", response_model=ProductBuildRun, status_code=status.HTTP_202_ACCEPTED)
def start_product_build(req: ProductBuildRequest):
    """Launches an end-to-end autonomous product build run with automated testing & self-correction."""
    try:
        return product_builder_engine.create_product_build(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/product-builder/builds", response_model=List[ProductBuildRun])
def list_builds():
    """Lists all product build runs."""
    return product_builder_engine.list_builds()


@router.get("/product-builder/builds/{build_id}", response_model=ProductBuildRun)
def get_build(build_id: str):
    """Retrieves detailed status, logs, and artifacts of a specific product build run."""
    build = product_builder_engine.get_build(build_id)
    if not build:
        raise HTTPException(status_code=404, detail=f"Build run {build_id} not found")
    return build


@router.post("/product-builder/builds/{build_id}/repair", response_model=ProductBuildRun)
def trigger_build_repair(build_id: str, reason: str = Query("Manual repair request", description="Reason for repair")):
    """Triggers an autonomous self-correction repair iteration for a build run."""
    try:
        return product_builder_engine.repair_build(build_id, reason=reason)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/product-builder/specs", response_model=List[ProductSpecification])
def list_specs():
    """Lists all synthesized product specifications."""
    return product_builder_engine.list_specs()


@router.get("/product-builder/specs/{spec_id}", response_model=ProductSpecification)
def get_spec(spec_id: str):
    """Retrieves a specific product specification."""
    spec = product_builder_engine.get_spec(spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Specification {spec_id} not found")
    return spec


@router.get("/product-builder/catalog", response_model=List[Dict[str, Any]])
def get_catalog():
    """Lists delivered products in the factory catalog ready for deployment."""
    return product_builder_engine.get_catalog()


@router.get("/product-builder/telemetry", response_model=ProductBuilderTelemetry)
def get_telemetry():
    """Returns factory operational telemetry and FinOps zero-cost status."""
    return product_builder_engine.get_telemetry()


@router.get("/product-builder/health")
def health_check():
    """Product Builder engine health and FinOps invariant status."""
    telem = product_builder_engine.get_telemetry()
    return {
        "status": "HEALTHY",
        "subsystem": "product_builder_engine",
        "finops_zero_cost_verified": telem.finops_zero_cost_verified,
        "total_products_built": telem.total_products_built,
        "active_builds": telem.active_builds,
        "successful_deliveries": telem.successful_deliveries
    }
