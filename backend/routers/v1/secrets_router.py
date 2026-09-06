from fastapi import APIRouter
from typing import List, Dict, Any
from core.secrets import secret_manager

router = APIRouter(prefix="/secrets", tags=["Secrets"])

@router.get("", response_model=List[Dict[str, Any]])
def list_secrets_status():
    """Returns safe metadata list of configured secrets (zero values exposed)."""
    return secret_manager.list_secrets_metadata()

@router.get("/{name}/status")
def get_secret_status(name: str):
    """Checks whether a given secret is populated."""
    configured = secret_manager.is_configured(name)
    return {
        "name": name,
        "configured": configured,
        "status": "CONFIGURED" if configured else "PENDING_SETUP"
    }
