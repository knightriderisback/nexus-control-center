import subprocess
import os
from typing import Dict, Any, List

def get_git_repo_info(repo_path: str) -> Dict[str, Any]:
    git_dir = os.path.join(repo_path, ".git")
    if not os.path.exists(git_dir):
        return {"has_git": False, "path": repo_path}

    info = {
        "has_git": True,
        "path": repo_path,
        "branch": "main",
        "last_commit": "None",
        "uncommitted_changes": 0,
        "remote_url": "unknown"
    }

    try:
        b = subprocess.run(["git", "branch", "--show-current"], cwd=repo_path, capture_output=True, text=True, timeout=5)
        info["branch"] = b.stdout.strip() or "main"

        c = subprocess.run(["git", "log", "-1", "--format=%h - %s (%cr)"], cwd=repo_path, capture_output=True, text=True, timeout=5)
        info["last_commit"] = c.stdout.strip()

        s = subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True, timeout=5)
        changes = [l for l in s.stdout.split("\n") if l.strip()]
        info["uncommitted_changes"] = len(changes)

        r = subprocess.run(["git", "remote", "get-url", "origin"], cwd=repo_path, capture_output=True, text=True, timeout=5)
        info["remote_url"] = r.stdout.strip() or "local"
    except Exception as e:
        info["error"] = str(e)

    return info

def list_known_repositories() -> List[Dict[str, Any]]:
    candidate_paths = ["/root/control-center", "/root/portfolio", "/root/mera_project"]
    results = []
    for p in candidate_paths:
        if os.path.exists(p):
            results.append(get_git_repo_info(p))
    return results
