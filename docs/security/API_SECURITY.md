# Control Plane API & WebSocket Security

## 1. Overview & Status
The NEXUS Control Plane enforces provider-neutral authentication and strict CORS boundary controls across all HTTP routes (`/api/v1/*`) and WebSocket connections (`/ws`).

- **API Authentication**: REAL
- **WebSocket Pre-Accept Authentication**: REAL
- **CORS Configuration**: REAL (Fixed, wildcard disabled)
- **Token Leakage Defense**: REAL (Constant-time verification, zero credentials in logs)

## 2. Authentication Provider Architecture

The authentication subsystem is implemented in `backend/core/auth.py` via an extensible `AuthProvider` interface:

```python
class AuthProvider(ABC):
    @abstractmethod
    def verify_token(self, token: str) -> bool: ...

    @abstractmethod
    def get_identity(self, token: str) -> Optional[str]: ...
```

### Supported Implementations:
1. **`LocalTokenAuthProvider` (Active)**:
   - Evaluates Bearer tokens against the configured `AUTH_SECRET_KEY` in `config.py`.
   - Uses `secrets.compare_digest` to eliminate timing attack vectors.
   - Rejects missing, malformed, or unauthorized tokens with HTTP 401 Unauthorized.
2. **`CloudIAMAuthProvider` (Ready for Cloud Migration)**:
   - Designed for Google Cloud IAM verification using OAuth2/OIDC.
   - In the current local phase, returns `False` safely without attempting external network calls.

## 3. Route Protection Matrix

All endpoints under `/api/v1/*` depend on `require_auth` in `backend/core/auth.py`:

| Endpoint Category | Method | Authentication Required | Enforced By |
| :--- | :--- | :--- | :--- |
| `/api/v1/overview` | GET | Yes | `require_auth` dependency |
| `/api/v1/projects/*` | ALL | Yes | `require_auth` dependency |
| `/api/v1/agents/*` | ALL | Yes | `require_auth` dependency |
| `/api/v1/approvals/*` | ALL | Yes | `require_auth` dependency |
| `/api/v1/cost/*` | ALL | Yes | `require_auth` dependency |
| `/api/v1/metrics` | GET | Yes | `require_auth` dependency |
| `/api/v1/traces` | GET | Yes | `require_auth` dependency |
| `/ws` | WEBSOCKET | Yes (Pre-accept) | Query param `?token=` or Header `Authorization` |
| `/health` | GET | No | Public health probe |

## 4. WebSocket Security Hardening

To prevent unauthorized connection hijacking, `server.py` verifies credentials **before** accepting the socket connection:
- Rejects missing or invalid tokens with WebSocket closure code `1008` (Policy Violation).
- Does not accept the handshake or allocate frame buffers for unauthenticated peers.

## 5. CORS Hardening

Wildcard origins with credentials have been eliminated:
- `allow_origins`: Strictly bound to `config.allowed_origins` (defaults to `["http://localhost:5173", "http://127.0.0.1:5173"]`).
- `allow_credentials`: Enabled only for explicit origins.
- `allow_methods`: Restricted to standard REST methods (`GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`).
- `allow_headers`: Standard authorization and content headers.
