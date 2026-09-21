"""
NEXUS external project source synchronization.

Sources intentionally limited to GitHub and Vercel.  Authentication is delegated
to the local Ubuntu/Termux CLIs (gh and vercel), so no provider token is stored in
the NEXUS registry or exposed to the frontend.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from orchestrator.safe_runner import SafeCommandExecutor
from registry.projects import load_projects, save_projects
from models.schemas import ProjectRegistryItem, ProjectStatus

logger = logging.getLogger("nexus.external_sources")


def _run_json(command: List[str]) -> Tuple[Optional[Any], Optional[str]]:
    result = SafeCommandExecutor.execute(command)
    if result.exit_code != 0:
        return None, (result.stderr or result.stdout or f"command failed: {command[0]}").strip()
    raw = (result.stdout or "").strip()
    if not raw:
        return None, None
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON from {' '.join(command[:3])}: {exc}"


def _norm(value: Optional[str]) -> str:
    if not value:
        return ""
    value = value.lower().strip().rstrip("/")
    value = re.sub(r"^https?://(www\\.)?github\\.com/", "", value)
    value = re.sub(r"^git@github\\.com:", "", value)
    value = re.sub(r"\\.git$", "", value)
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def _github_repo_from_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    m = re.search(r"github\\.com[/:]([^/]+)/([^/#]+?)(?:\\.git)?$", value.strip())
    return f"{m.group(1)}/{m.group(2)}" if m else None


def discover_github() -> Tuple[List[Dict[str, Any]], List[str]]:
    data, error = _run_json([
        "gh", "repo", "list", "--limit", "100",
        "--json", "name,nameWithOwner,defaultBranchRef,isPrivate,isArchived,url,sshUrl,pushedAt"
    ])
    if error:
        return [], [f"GitHub: {error}"]
    if not isinstance(data, list):
        return [], ["GitHub: unexpected gh repo list response"]
    repos = []
    for item in data:
        if item.get("isArchived"):
            continue
        full = item.get("nameWithOwner") or ""
        repos.append({
            "id": f"github:{full}",
            "name": item.get("name") or full.split("/")[-1],
            "github_repo": full,
            "repository": item.get("sshUrl") or item.get("url"),
            "branch": (item.get("defaultBranchRef") or {}).get("name") or "main",
            "visibility": "private" if item.get("isPrivate") else "public",
            "url": item.get("url"),
            "pushed_at": item.get("pushedAt"),
            "source": "github",
        })
    return repos, []


def discover_vercel() -> Tuple[List[Dict[str, Any]], List[str]]:
    teams, error = _run_json(["vercel", "api", "GET", "/v2/teams"])
    if error:
        return [], [f"Vercel: {error}"]

    team_list = teams.get("teams", []) if isinstance(teams, dict) else []
    if not team_list:
        return [], ["Vercel: no accessible teams returned"]

    team_id = None
    preferred = __import__("os").environ.get("VERCEL_TEAM_ID")
    if preferred:
        team_id = preferred
    else:
        team_id = team_list[0].get("id")

    projects, error = _run_json([
        "vercel", "api", "GET", f"/v9/projects?teamId={team_id}&limit=100"
    ])
    if error:
        return [], [f"Vercel: {error}"]

    raw_projects = projects.get("projects", []) if isinstance(projects, dict) else []
    result: List[Dict[str, Any]] = []

    for item in raw_projects:
        project_id = item.get("id")
        name = item.get("name") or project_id or "vercel-project"
        link = item.get("link") or {}
        repo = None
        if isinstance(link, dict):
            org = link.get("org") or link.get("owner")
            linked_repo = link.get("repo")
            if org and linked_repo:
                repo = f"{org}/{linked_repo}"

        result.append({
            "id": f"vercel:{project_id or name}",
            "name": name,
            "vercel_project_id": project_id,
            "github_repo": repo,
            "repository": f"https://github.com/{repo}.git" if repo else None,
            "branch": (link.get("productionBranch") if isinstance(link, dict) else None) or "main",
            "url": None,
            "source": "vercel",
            "deployment_provider": "Vercel",
        })

    return result, []


def _match_project(projects: List[ProjectRegistryItem], item: Dict[str, Any]) -> Optional[ProjectRegistryItem]:
    target_repo = _norm(item.get("github_repo") or item.get("repository"))
    target_name = _norm(item.get("name"))

    for project in projects:
        project_repo = _norm(getattr(project, "github_repo", None) or getattr(project, "repository", None))
        if target_repo and project_repo and target_repo == project_repo:
            return project

    for project in projects:
        if target_name and _norm(project.name) == target_name:
            return project

    return None


def sync_external_sources() -> Dict[str, Any]:
    """
    Pulls the current GitHub and Vercel inventories from the authenticated local
    CLIs and merges them idempotently into the NEXUS registry.
    """
    github, github_errors = discover_github()
    vercel, vercel_errors = discover_vercel()
    discovered = github + vercel
    errors = github_errors + vercel_errors

    projects = load_projects()
    added = 0
    updated = 0
    merged = 0
    seen_external = set()

    for item in discovered:
        seen_external.add(item["id"])
        existing = _match_project(projects, item)

        if existing:
            sources = set(getattr(existing, "sources", []) or [])
            sources.add(item["source"])
            existing.sources = sorted(sources)
            existing.tags = sorted(set((existing.tags or []) + ["external-sync", f"source:{item['source']}"]))

            if item.get("github_repo"):
                existing.github_repo = item["github_repo"]
                existing.repository = item.get("repository") or existing.repository
            if item.get("branch"):
                existing.branch = item["branch"]
            if item["source"] == "vercel":
                existing.deployment_provider = "Vercel"
            updated += 1
            merged += 1
            continue

        source = item["source"]
        external_id = item["id"].replace(":", "-")
        external_path = f"/__nexus_external__/{source}/{external_id}"

        reg = ProjectRegistryItem(
            id=external_id,
            name=item["name"],
            path=external_path,
            github_repo=item.get("github_repo"),
            repository=item.get("repository"),
            branch=item.get("branch") or "main",
            type="external",
            environment="external",
            deployment_provider=item.get("deployment_provider") or ("GitHub" if source == "github" else "Vercel"),
            domain=item.get("url"),
            status=ProjectStatus.ACTIVE,
            health_score=100,
            owner="knightriderisback",
            description=f"Externally discovered from {source}.",
            tags=["external-sync", f"source:{source}"],
            sources=[source],
        )
        projects.append(reg)
        added += 1

    save_projects(projects)

    return {
        "status": "COMPLETED" if discovered or not errors else "FAILED",
        "github_discovered": len(github),
        "vercel_discovered": len(vercel),
        "total_discovered": len(discovered),
        "added_count": added,
        "updated_count": updated,
        "merged_count": merged,
        "errors": errors,
    }
