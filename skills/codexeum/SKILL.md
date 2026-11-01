---
name: codexeum
description: Launch the Codexeum terminal pet quiz arena to create a room, join a room, or pair an existing website player with local Codex.
---

Launch the interactive arena requested by the user. `new` creates a room; a six-character room code joins as player two; a `P-` pairing code connects the user's existing website player seat. Default to `new` when no argument is supplied.

Resolve this skill's real directory (follow its symlink). The repository root is two directories above it. Use the root's `scripts/launch_codexeum.py` with the target as a separate argument. Pass the user's arena URL with `--url` when supplied, otherwise use `CODEXEUM_URL`; the local-development default is http://localhost:5001. Never guess a production hostname. The arena form also permits entering the URL before connecting.

For example: `python3 <repo>/scripts/launch_codexeum.py new --url https://<user-supplied-host>`.

If terminal dependencies are missing, run `uv sync --extra tui` in that repository. The launcher opens a visible terminal window. Do not run a full-screen TUI in a captured agent shell and claim the user can see it. If window launch is unavailable, provide the exact command to run in the user's terminal.

The TUI asks for a nickname and specialty, displays the room code, and offers READY and START BATTLE. It drives a separate local Codex App Server conversation to answer automatically. The user can press A–D to answer manually or Space to pause autoplay. Q closes it. Do not independently answer questions or poll the room from this launcher chat.

Custom pet artwork may be supplied with `--pet <local pet directory or image>`. A single local custom pet under CODEX_HOME/pets is discovered automatically; multiple pets require a selection via that argument. The client uses the first idle frame of supported sprite sheets. Do not claim to have read the current Codex pet selection when only a local folder was found.

The local Codex CLI must already be installed and signed in. Its credentials stay with Codex; do not request or transfer them to the arena. If no arena URL or local server is available, the TUI can open but cannot enter a room. Verify the launcher result before reporting that the arena opened.
