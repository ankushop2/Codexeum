#!/usr/bin/env python3
"""Open a real terminal, rather than an agent's captured background PTY."""

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command(arguments):
    python = ROOT / ".venv/bin/python"
    if not python.is_file():
        raise RuntimeError("Run uv sync --extra tui in the Codexeum repository first.")
    result = subprocess.run(
        [str(python), "-c", "import textual, PIL, httpx"],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            "Terminal dependencies are missing. Run uv sync --extra tui first."
        )
    return [str(python), "-m", "codexeum", *arguments]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--here",
        action="store_true",
        help="Use this terminal instead of opening another",
    )
    parser.add_argument(
        "--print-command",
        action="store_true",
        help="Print the launch command without opening a terminal",
    )
    args, rest = parser.parse_known_args()
    try:
        argv = command(rest)
        if args.print_command:
            print(f"cd {shlex.quote(str(ROOT))} && {shlex.join(argv)}")
        elif args.here:
            subprocess.run(argv, cwd=ROOT, check=True)
        elif sys.platform == "darwin":
            run_dir = Path(tempfile.mkdtemp(prefix="codexeum-launch-"))
            script = run_dir / "Codexeum.command"
            # Arguments are quoted as shell data; no generated prompt is executable code.
            script.write_text(
                "#!/bin/sh\ncd "
                + shlex.quote(str(ROOT))
                + " || exit 1\n"
                + shlex.join(argv)
                + "\n"
            )
            script.chmod(0o700)
            subprocess.run(["open", "-a", "Terminal", str(script)], check=True)
            print("Opened Codexeum in Terminal. Close the arena with Q.")
        elif os.name == "nt":
            subprocess.Popen(
                argv, cwd=ROOT, creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            terminal = next(
                (
                    p
                    for p in ("x-terminal-emulator", "gnome-terminal", "xterm")
                    if shutil.which(p)
                ),
                None,
            )
            if not terminal:
                raise RuntimeError(
                    "No terminal launcher found. Run with --here in your terminal."
                )
            subprocess.Popen(
                [terminal, "--" if terminal == "gnome-terminal" else "-e", *argv],
                cwd=ROOT,
            )
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
