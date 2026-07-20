"""Module loader — discovers, validates, and manages Project Echo modules.

Each module is a directory with a module.yaml manifest. The loader scans
known locations for modules, validates their manifests, and reports what's
available for installation.
"""

import json
import os
from pathlib import Path

import yaml

# Standard module search paths
MODULE_PATHS = [
    Path("~/.echo-core/modules").expanduser(),
    Path("~/.echo-core/modules").expanduser(),
]


def discover_modules(paths: list[str] = None) -> list[dict]:
    """Scan module directories and return all discovered modules.

    Args:
        paths: List of directories to scan. Uses defaults if not provided.

    Returns:
        List of module manifests (dicts from module.yaml), each with
        an added 'path' field pointing to the module directory.
    """
    search_paths = [Path(p).expanduser() for p in (paths or MODULE_PATHS)]
    modules = []

    for sp in search_paths:
        if not sp.exists():
            continue
        for item in sorted(sp.iterdir()):
            if not item.is_dir():
                continue
            manifest_path = item / "module.yaml"
            if not manifest_path.exists():
                continue
            try:
                with open(manifest_path) as f:
                    manifest = yaml.safe_load(f)
                if manifest and isinstance(manifest, dict):
                    manifest["_path"] = str(item)
                    modules.append(manifest)
            except (yaml.YAMLError, OSError):
                continue

    return modules


def load_module_manifest(module_name: str, paths: list[str] = None) -> dict | None:
    """Load a specific module's manifest by name.

    Args:
        module_name: Name of the module (matches module.yaml 'name' field).
        paths: List of directories to search.

    Returns:
        Module manifest dict, or None if not found.
    """
    for module in discover_modules(paths):
        if module.get("name") == module_name:
            return module
    return None


def validate_module(manifest: dict) -> list[str]:
    """Validate a module manifest for required fields and structure.

    Returns a list of validation errors (empty if valid).
    """
    errors = []

    required_fields = ["name", "version", "description"]
    for field in required_fields:
        if field not in manifest:
            errors.append(f"Missing required field: '{field}'")

    if "tools_required" in manifest and isinstance(manifest["tools_required"], list):
        for tool in manifest["tools_required"]:
            if "command" not in tool:
                errors.append(f"Tool entry missing 'command': {tool}")

    if "python_deps" in manifest and not isinstance(manifest["python_deps"], list):
        errors.append("'python_deps' must be a list")

    if "skills" in manifest and not isinstance(manifest["skills"], list):
        errors.append("'skills' must be a list")

    return errors


def module_status(module_name: str, paths: list[str] = None) -> dict:
    """Get the installation status of a module.

    Returns a dict with: name, found (bool), valid (bool), errors (list),
    installed (bool), and manifest (dict if found).
    """
    manifest = load_module_manifest(module_name, paths)
    if not manifest:
        return {
            "name": module_name,
            "found": False,
            "valid": False,
            "installed": False,
            "errors": ["Module not found in search paths"],
        }

    errors = validate_module(manifest)

    # Check if installed by verifying the install marker
    module_dir = Path(manifest.get("_path", ""))
    installed = (module_dir / ".installed").exists()

    return {
        "name": module_name,
        "found": True,
        "valid": len(errors) == 0,
        "installed": installed,
        "errors": errors,
        "manifest": manifest,
    }


def list_available_modules(paths: list[str] = None) -> list[dict]:
    """List all modules with their status.

    Each entry includes: name, version, description, valid, installed, errors.
    """
    modules = discover_modules(paths)
    return [module_status(m["name"]) for m in modules]


def add_module_path(path: str):
    """Add a directory to the module search paths."""
    p = Path(path).expanduser()
    if p not in MODULE_PATHS:
        MODULE_PATHS.append(p)


def install_module(module_name: str, paths: list[str] = None) -> dict:
    """Install a module by marking it as installed.

    This is a lightweight install — it creates a .installed marker
    and copies scripts to the echo-core directory as specified in the
    module's files section.

    Args:
        module_name: Name of the module to install.
        paths: Module search paths.

    Returns:
        dict with status, module_name, errors (if any).
    """
    manifest = load_module_manifest(module_name, paths)
    if not manifest:
        return {"status": "failed", "module_name": module_name,
                "errors": ["Module not found"]}

    errors = validate_module(manifest)
    if errors:
        return {"status": "failed", "module_name": module_name,
                "errors": errors}

    module_dir = Path(manifest.get("_path", ""))
    if not module_dir.exists():
        return {"status": "failed", "module_name": module_name,
                "errors": ["Module directory not found"]}

    # Create .installed marker
    (module_dir / ".installed").write_text(
        json.dumps({"installed_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat()})
    )

    # Copy scripts if specified
    for file_entry in manifest.get("files", []):
        src = module_dir / file_entry.get("source", "")
        target = Path(file_entry.get("target", "")).expanduser()
        if src.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(src.read_text())

    # Create directories if specified
    for dir_entry in manifest.get("directories", []):
        Path(dir_entry).expanduser().mkdir(parents=True, exist_ok=True)

    return {"status": "installed", "module_name": module_name, "errors": []}


def uninstall_module(module_name: str, paths: list[str] = None) -> dict:
    """Uninstall a module by removing its .installed marker."""
    manifest = load_module_manifest(module_name, paths)
    if not manifest:
        return {"status": "failed", "module_name": module_name,
                "errors": ["Module not found"]}

    module_dir = Path(manifest.get("_path", ""))
    marker = module_dir / ".installed"
    if marker.exists():
        marker.unlink()

    return {"status": "uninstalled", "module_name": module_name, "errors": []}