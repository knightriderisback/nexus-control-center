"""
NEXUS Provider-Neutral Authentication Layer.
Provides secure token validation for Control API (/api/v1/*) and WebSocket (/ws).

Features:
- Provider-neutral AuthProvider interface (Local Token, Cloud IAM/OIDC).
- Local operator token resolution from environment/SecretManager.
- Constant-time token verification (preventing timing attacks).
- Complete token masking (zero secret leakage in logs/traces).
- Support for Bearer Authorization and X-NEXUS-KEY headers.
- Query-parameter and header authentication for WebSockets prior to connection acceptance.
"""

import os
import hmac
import secrets
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Security, WebSocket, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.config import config
from core.secrets import secret_manager
from core.audit import record_audit
from models.schemas import RiskLevel

# Development fallback token if none provided in environment
DEFAULT_DEV_TOKEN = "nexus-dev-operator-key-2026"

class AuthUser:
    def __init__(self, username: str, role: str, auth_type: str):
        self.username = username
        self.role = role
        self.auth_type = auth_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "role": self.role,
            "auth_type": self.auth_type
        }

class AuthProvider(ABC):
    @abstractmethod
    def verify_token(self, token: str) -> Optional[AuthUser]:
        """Validates credential string and returns AuthUser if valid."""
        pass

class LocalTokenAuthProvider(AuthProvider):
    """
    Validates requests against locally configured operator token.
    Uses constant-time comparison to prevent timing attacks.
    """
    def __init__(self):
        token = secret_manager.get_secret("NEXUS_OPERATOR_TOKEN") or os.getenv("NEXUS_OPERATOR_TOKEN")
        if not token:
            token = DEFAULT_DEV_TOKEN
        self._expected_token = token

    def verify_token(self, token: str) -> Optional[AuthUser]:
        if not token:
            return None
        # Constant-time comparison
        if hmac.compare_digest(token.strip(), self._expected_token.strip()):
            return AuthUser(username="operator", role="admin", auth_type="LOCAL_TOKEN")
        return None

class CloudIAMAuthProvider(AuthProvider):
    """
    Staged interface for Google Cloud IAM OIDC validation.
    When deployed behind Cloud Run or IAP, validates JWT tokens without hardcoded credentials.
    """
    def __init__(self, audience: Optional[str] = None):
        self.audience = audience or config.gcp_project_id

    def verify_token(self, token: str) -> Optional[AuthUser]:
        if not token or len(token) < 20:
            return None
        # In mock/offline mode, return None to defer to local auth
        return None

class AuthManager:
    """Coordinates authentication providers and enforces security policy."""

    def __init__(self):
        self.local_provider = LocalTokenAuthProvider()
        self.cloud_provider = CloudIAMAuthProvider()

    def authenticate_token(self, token: Optional[str]) -> Optional[AuthUser]:
        if not token:
            return None
        
        # Clean potential 'Bearer ' prefix
        clean_token = token
        if clean_token.lower().startswith("bearer "):
            clean_token = clean_token[7:].strip()

        # 1. Check local token provider
        user = self.local_provider.verify_token(clean_token)
        if user:
            return user

        # 2. Check cloud IAM provider
        user = self.cloud_provider.verify_token(clean_token)
        if user:
            return user

        return None

auth_manager = AuthManager()
bearer_scheme = HTTPBearer(auto_error=False)

def extract_token_from_request(request: Request) -> Optional[str]:
    """Safely extracts credential token from headers without logging."""
    auth_header = request.headers.get("Authorization")
    if auth_header:
        if auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()
        return auth_header.strip()

    nexus_key = request.headers.get(config.api_key_header)
    if nexus_key:
        return nexus_key.strip()

    return None

async def require_auth(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency for protecting /api/v1/* endpoints.
    Enforces authentication when config.auth_enabled is True.
    When config.auth_enabled is False, validates token if present, or allows local dev operator.
    """
    token = extract_token_from_request(request)

    if token:
        user = auth_manager.authenticate_token(token)
        if not user:
            record_audit(
                action="AUTH_FAILED",
                project="control-center",
                target=request.url.path,
                reason="Invalid authentication credentials presented",
                risk_level=RiskLevel.MEDIUM,
                result="DENIED"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return user.to_dict()

    if config.auth_enabled:
        record_audit(
            action="AUTH_REQUIRED",
            project="control-center",
            target=request.url.path,
            reason="Unauthenticated request to protected endpoint",
            risk_level=RiskLevel.LOW,
            result="DENIED"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Local open development fallback when auth_enabled is explicitly False
    return {
        "username": "local_dev_operator",
        "role": "admin",
        "auth_type": "LOCAL_DEV_OPEN"
    }

async def authenticate_websocket(websocket: WebSocket) -> Optional[Dict[str, Any]]:
    """
    Validates credentials for incoming WebSocket connection before accept().
    Accepts token via 'token' query param, 'Authorization' header, or 'X-NEXUS-KEY' header.
    """
    token = websocket.query_params.get("token")
    if not token:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
        elif auth_header:
            token = auth_header.strip()

    if not token:
        token = websocket.headers.get(config.api_key_header.lower())

    if token:
        user = auth_manager.authenticate_token(token)
        if user:
            return user.to_dict()
        return None

    if config.auth_enabled:
        return None

    return {
        "username": "local_dev_ws_operator",
        "role": "admin",
        "auth_type": "LOCAL_DEV_OPEN"
    }
