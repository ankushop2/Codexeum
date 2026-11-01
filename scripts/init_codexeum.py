#!/usr/bin/env python3
"""Install the Codexeum skill and its terminal dependencies."""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "codexeum"


def main():
    uv = shutil.which("uv")
    if not uv:
        sys.exit("uv is required. Install it from https://docs.astral.sh/uv/getting-started/installation/ and run this command again.")

    destination = Path.home() / ".agents" / "skills" / "codexeum"
    if destination.is_symlink():
        if destination.resolve() != SKILL:
            sys.exit(f"{destination} already points elsewhere. Remove or rename it before installing.")
    elif destination.exists():
        sys.exit(f"{destination} already exists. Remove or rename it before installing.")

    subprocess.run([uv, "sync", "--extra", "tui"], cwd=ROOT, check=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.is_symlink():
        destination.symlink_to(SKILL, target_is_directory=True)
    print(f"Codexeum skill installed at {destination}")
    print("Open a new Codex session, then use $codexeum new. The Codex CLI must be installed and signed in.")


if __name__ == "__main__":
    main()
