"""A factual receipt of the actual Python/direct-package versions used in CI.

This does not lock transitive dependencies or assert reproducibility across
future resolver runs; it records what *was installed* and tested.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements.txt"
PATTERN = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)")


def make_receipt(requirements_text: str, *, versions=None, python_version=None,
                 source_commit=None, generated_at=None) -> dict:
    """Fail if any non-comment direct requirement is absent from the environment."""
    version_getter = versions or metadata.version
    packages = {}
    for raw in requirements_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = PATTERN.match(line)
        if not match:
            raise ValueError(f"Unsupported requirements entry: {line!r}")
        package = match.group(1)
        if package in packages:
            raise ValueError(f"Duplicate direct dependency: {package}")
        try:
            packages[package] = str(version_getter(package))
        except metadata.PackageNotFoundError as exc:
            raise RuntimeError(f"Missing installed dependency: {package}") from exc
    if not packages:
        raise ValueError("No direct dependencies found")
    return {
        "audit_type": "tested direct runtime versions; NOT a dependency lock",
        "python_version": python_version or sys.version.split()[0],
        "requirements_sha256": hashlib.sha256(
            requirements_text.encode("utf-8")).hexdigest(),
        "direct_dependency_versions": packages,
        "source_commit": source_commit,
        "generated_at_utc": generated_at or datetime.now(
            timezone.utc).isoformat(),
        "known_limitation": (
            "Resolver-selected transitive packages are not pinned; another "
            "installation can choose different versions within requirement ranges."
        ),
    }


def main() -> dict:
    raw = REQUIREMENTS.read_text(encoding="utf-8")
    output = make_receipt(raw, source_commit=os.environ.get("GITHUB_SHA"))
    target = ROOT / "tested-runtime.json"
    target.write_text(json.dumps(output, indent=2, sort_keys=True),
                      encoding="utf-8")
    print("TESTED ENVIRONMENT:", json.dumps(output, sort_keys=True))
    return output


if __name__ == "__main__":
    main()
