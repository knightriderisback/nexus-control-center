"""
NEXUS Phase 15: Universal Tool & App Integration REST API Router.
Mounted under /api/v1/tools.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from models.schemas import (
    UniversalToolManifest,
    UniversalToolInvocationRequest,
    UniversalToolInvocationResult,
    ConnectedApp,
    MCPServerDefinition,
)
from orchestrator.universal_tool_engine import universal_tool_engine

router = APIRouter(prefix="/tools", tags=["Universal Tools & Apps"])


@router.get("", response_model=List[UniversalToolManifest])
def list_universal_tools(
    category: Optional[str] = Query(None, description="Filter by category (FILESYSTEM, GIT_VCS, DEPLOYMENT, DATABASE, SECURITY, COMMUNICATION, WEB_BROWSER, SYSTEM_OS, CUSTOM_PLUGIN)"),
    protocol: Optional[str] = Query(None, description="Filter by protocol (NATIVE_PYTHON, REST_API, CLI_EXECUTABLE, MCP_STDIO, DATABASE_QUERY, WEBHOOK)"),
    risk_level: Optional[str] = Query(None, description="Filter by risk tier (LOW, MEDIUM, HIGH, CRITICAL)"),
    enabled_only: bool = Query(True, description="Filter active tools only")
):
    """Lists all registered universal tools with dynamic filtering."""
    return universal_tool_engine.list_tools(
        category=category,
        protocol=protocol,
        risk_level=risk_level,
        enabled_only=enabled_only
    )


@router.get("/telemetry")
def get_universal_tools_telemetry():
    """Returns aggregated invocation statistics and performance telemetry."""
    return universal_tool_engine.get_telemetry()


@router.get("/apps", response_model=List[ConnectedApp])
def list_connected_apps():
    """Lists all external connected apps and ecosystems."""
    return universal_tool_engine.list_connected_apps()


@router.post("/apps/{app_id}/test")
def test_connected_app(app_id: str):
    """Tests connectivity to a specific external connected app."""
    try:
        return universal_tool_engine.test_app_connection(app_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/servers", response_model=List[MCPServerDefinition])
def list_mcp_servers():
    """Lists all registered Model Context Protocol (MCP) servers."""
    return universal_tool_engine.list_mcp_servers()


@router.post("/mcp/servers", response_model=MCPServerDefinition)
def register_mcp_server(server: MCPServerDefinition):
    """Registers a new MCP server definition."""
    return universal_tool_engine.register_mcp_server(server)


@router.post("/mcp/servers/{server_id}/connect", response_model=MCPServerDefinition)
def connect_mcp_server(server_id: str):
    """Connects to an MCP server and queries exposed tools."""
    try:
        return universal_tool_engine.connect_mcp_server(server_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tool_id}", response_model=UniversalToolManifest)
def get_universal_tool(tool_id: str):
    """Fetches details and input/output schemas for a specific tool."""
    tool = universal_tool_engine.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found.")
    return tool


@router.post("/{tool_id}/invoke", response_model=UniversalToolInvocationResult)
def invoke_universal_tool(tool_id: str, req: UniversalToolInvocationRequest):
    """Executes a universal tool invocation through the governed engine."""
    req.tool_id = tool_id
    result = universal_tool_engine.invoke_tool(req)
    return result


@router.post("/register", response_model=UniversalToolManifest)
def register_custom_tool(manifest: UniversalToolManifest):
    """Registers a custom universal tool or plugin manifest."""
    return universal_tool_engine.register_tool(manifest)


@router.delete("/{tool_id}")
def unregister_universal_tool(tool_id: str):
    """Unregisters a tool by ID."""
    success = universal_tool_engine.unregister_tool(tool_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found.")
    return {"status": "UNREGISTERED", "tool_id": tool_id}
