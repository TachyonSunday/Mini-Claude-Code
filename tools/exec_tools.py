"""Execution tools: run_command, run_tests. Sandboxed to workspace directory."""

import subprocess
import os
from pathlib import Path

WORKSPACE_ROOT = None
DANGEROUS_KEYWORDS = [
    "rm -rf /", "mkfs.", "dd if=", ":(){ :|:& };:", "fork bomb",
    "chmod -R 777 /", "> /dev/sda", "shutdown", "reboot",
    "curl", "wget",
]


def set_workspace(path: str) -> None:
    global WORKSPACE_ROOT
    WORKSPACE_ROOT = Path(path).resolve()
    os.makedirs(WORKSPACE_ROOT, exist_ok=True)


def _is_dangerous(cmd: str) -> bool:
    cmd_lower = cmd.lower()
    for kw in DANGEROUS_KEYWORDS:
        if kw in cmd_lower:
            return True
    return False


def run_command(cmd: str, timeout: int = 30) -> dict:
    """Execute a shell command in the workspace directory."""
    if WORKSPACE_ROOT is None:
        return {"success": False, "error": "Workspace not set."}
    if _is_dangerous(cmd):
        return {"success": False, "error": f"Command blocked by safety filter: {cmd}"}
    try:
        r = subprocess.run(
            cmd, shell=True, cwd=str(WORKSPACE_ROOT),
            capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "PYTHONPATH": str(WORKSPACE_ROOT)},
        )
        return {
            "success": r.returncode == 0,
            "stdout": r.stdout[-4000:] if len(r.stdout) > 4000 else r.stdout,
            "stderr": r.stderr[-2000:] if len(r.stderr) > 2000 else r.stderr,
            "returncode": r.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_tests(test_path: str = ".") -> dict:
    """Run Python tests with pytest in the workspace."""
    if WORKSPACE_ROOT is None:
        return {"success": False, "error": "Workspace not set."}
    try:
        r = subprocess.run(
            ["python", "-m", "pytest", test_path, "-v", "--tb=short"],
            cwd=str(WORKSPACE_ROOT), capture_output=True, text=True, timeout=60,
            env={**os.environ, "PYTHONPATH": str(WORKSPACE_ROOT)},
        )
        return {
            "success": r.returncode == 0,
            "stdout": r.stdout[-6000:] if len(r.stdout) > 6000 else r.stdout,
            "stderr": r.stderr[-2000:] if len(r.stderr) > 2000 else r.stderr,
            "returncode": r.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Tests timed out after 60s"}
    except Exception as e:
        return {"success": False, "error": str(e)}
