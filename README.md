# Codex Arena

Your pet. Your skills. Your move.

Codex Arena is a two-player, turn-based pet battle concept where knowledge powers attacks. Each player brings a pet, picks a skill category, and faces five questions. Codex answers for your pet, and you can step in when it needs help. The battle shows the answers and results so you can follow how each move plays out.

The intended experience takes inspiration from retro creature battles: two pets facing off, health bars, skill choices, and a dialogue box narrating the action.

## How a match will work

1. Enter a nickname, choose or import a pet avatar, and create or join a room.
2. Choose a specialty from seven categories: Debugging, Python, JavaScript, Logic, Web, Data, or Security. Both players also receive a shared random category.
3. Play five question rounds. Each pet attempts an answer using Codex.
4. Help your pet when it cannot answer. Human intervention is part of the battle; its limits and scoring are still being designed.
5. Reveal the answers and resolve the attacks. See the match result and compete on a nickname-based leaderboard.

Room events and round updates are intended to reach both players in real time over sockets. Pet imports refer to avatar artwork, not access to a player's Codex account or conversation history.

## Current status

This repository currently provides a working frontend/API foundation. You can open the arena preview, see two animated placeholder pets and health bars, select one of seven categories loaded from Flask, and preview your selection.

The full match flow is planned. Pet importing, rooms, socket communication, question rounds, Codex answers, human assists, scoring, and the leaderboard are not implemented yet.

## Stack

- **Frontend:** React, TypeScript, Vite, CSS, and Motion for animation.
- **Backend:** Flask, with Python dependencies managed by uv.
- **Deployment:** One Docker image serving the built React app and Flask API through Gunicorn on the same origin.

## Local development

Requires Node.js 24, pnpm 10.23, uv, and Python 3.12 (uv can install Python).

```sh
pnpm install --frozen-lockfile
uv sync --python 3.12
pnpm dev
```

Open http://localhost:5173. Vite forwards `/api` to Flask on port 5001. No credentials are needed for the foundation preview.

## Included primitives

- Button and Panel for actions and layout.
- HealthBar with accessible progress values.
- PetAvatar with original CSS placeholder creatures and idle animation.
- SkillCard with keyboard focus and selected state.
- Seven categories fetched from `/api/skills`, plus `/api/health`.
- Responsive arena preview with explicit loading/error states.

## Basic checks

```sh
pnpm build
pnpm format:check
uv run python -c "from app import app; c = app.test_client(); print(c.get('/api/health').json); print(c.get('/api/skills').json); print(c.get('/').status_code)"
```

`pnpm build` typechecks and builds the frontend into `public/`. `pnpm format` formats frontend/configuration files and Python. No test suite or manual lint run is included.

## One deployment on Vercel

Import this repository with the repository root as Root Directory. `vercel.json` selects the Container framework preset. Vercel builds the root Dockerfile and runs one HTTP server serving React and `/api` together. The container listens on port 80 by default, matching Vercel routing. If you override PORT, set the matching environment variable in Vercel.

The Container runtime is currently beta. See [Vercel container deployment guidance](https://vercel.com/kb/guide/does-vercel-support-docker-deployments).

After deployment, check `/`, `/api/health`, `/api/skills`, and `/battle/preview`. Make sure deployment protection allows public access for the hackathon submission. No deployment has been performed yet.

## One Docker container

```sh
docker build -t codex-arena .
docker run --rm -p 8000:80 codex-arena
```

Open http://localhost:8000. The multi-stage image builds React, installs Python dependencies with uv, and serves both with Gunicorn as a non-root user. The `PORT` environment variable defaults to 80.

The same image can also run on other container hosts. The app works without a separate frontend host or CORS configuration.

## Integration boundaries

Keep answer keys, scoring, game rules, and Codex credentials on the server. Add durable database storage before shared matches or leaderboards; serverless instances do not share process memory or local disk. Run Centrifugo as an external real-time service and issue scoped connection tokens from Flask.

Pet artwork is presentation only; importing an avatar does not import a model, conversation, or account credentials. Replace PetAvatar with original or licensed sprites when ready.

## Credits

Created during the DevDay Community Hackathon in London on 1 November 2026. React/TypeScript scaffold generated using create-vite. Codex helped write the React primitives, Flask routes, and deployment configuration. The included pets are original CSS placeholders. No Pokémon assets are bundled. DM Sans and Space Grotesk are loaded from Google Fonts with system fallbacks. Dependencies retain their respective licenses.
