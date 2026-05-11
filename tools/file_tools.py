"""File tools: read_file, write_file, edit_file. All paths relative to workspace root."""

import os
from pathlib import Path

WORKSPACE_ROOT = None


def set_workspace(path: str) -> None:
    global WORKSPACE_ROOT
    WORKSPACE_ROOT = Path(path).resolve()


def _resolve(file_path: str) -> Path:
    if WORKSPACE_ROOT is None:
        raise RuntimeError("Workspace not set. Call set_workspace() first.")
    p = (WORKSPACE_ROOT / file_path).resolve()
    if not str(p).startswith(str(WORKSPACE_ROOT)):
        raise ValueError(f"Path traversal denied: {file_path}")
    return p


def read_file(file_path: str) -> dict:
    """Read file contents. Directories get listed instead."""
    try:
        p = _resolve(file_path)
        if not p.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        if p.is_dir():
            items = []
            for f in sorted(p.iterdir()):
                t = "dir" if f.is_dir() else "file"
                size = f.stat().st_size if f.is_file() else 0
                items.append(f"{f.name} ({t}, {size} bytes)")
            return {"success": True, "is_directory": True, "files": items, "path": str(p)}
        content = p.read_text(encoding="utf-8")
        lines = content.split("\n")
        numbered = "\n".join(f"{i+1:>4}|{line}" for i, line in enumerate(lines))
        return {"success": True, "content": numbered, "path": str(p), "lines": len(lines)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_file(file_path: str, content: str) -> dict:
    """Create or overwrite a file."""
    try:
        p = _resolve(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"success": True, "path": str(p), "size": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def edit_file(file_path: str, old: str, new: str) -> dict:
    """Replace old string with new in file. Fails if old is not unique."""
    try:
        p = _resolve(file_path)
        if not p.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        content = p.read_text(encoding="utf-8")
        count = content.count(old)
        if count == 0:
            return {"success": False, "error": "old string not found in file"}
        if count > 1:
            return {"success": False, "error": f"old string appears {count} times, must be unique"}
        new_content = content.replace(old, new, 1)
        p.write_text(new_content, encoding="utf-8")
        return {"success": True, "path": str(p), "replaced": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_diff() -> dict:
    """Show current git diff in workspace."""
    import subprocess
    try:
        r = subprocess.run(
            ["git", "-C", str(WORKSPACE_ROOT), "diff"],
            capture_output=True, text=True, timeout=10
        )
        return {"success": True, "diff": r.stdout if r.stdout else "(no changes)"}
    except Exception as e:
        return {"success": False, "error": str(e)}
