from fastapi import APIRouter
from typing import List, Dict, Any
from integrations.github import list_known_repositories, get_git_repo_info

router = APIRouter(prefix="/github", tags=["GitHub Integration"])

@router.get("/repos")
def get_repos() -> List[Dict[str, Any]]:
    return list_known_repositories()

@router.get("/repos/{project_name}/status")
def get_repo_status(project_name: str) -> Dict[str, Any]:
    path = f"/root/{project_name}"
    return get_git_repo_info(path)
