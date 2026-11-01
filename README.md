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

The frontend provides pet selection and image import, trainer naming, specialty selection, and a ready screen with practice question generation.

The game API supports rooms, five timed rounds and scoring with fixed questions. The multiplayer frontend is not connected yet. Practice questions use OpenAI; pet answers, human assists and the leaderboard are not implemented.

## Stack

- **Frontend:** React, TypeScript, Vite, CSS, and Motion for animation.
- **Backend:** FastAPI and the OpenAI Python SDK, with Python dependencies managed by uv.
- **Deployment:** One Docker image serving the built React app and FastAPI through Uvicorn on the same origin.

## Local development

Requires Node.js 24, pnpm 10.23, uv, and Python 3.12 (uv can install Python).

```sh
pnpm install --frozen-lockfile
uv sync --python 3.12
cp .env.example .env
# Set OPENAI_API_KEY in .env
pnpm dev
```

Open http://localhost:5173. Vite forwards `/api` to FastAPI on port 5001. Set `OPENAI_API_KEY` to generate questions; `OPENAI_MODEL` defaults to `gpt-4o-mini`. The arena and skills work without a key.

## Included primitives

- Button and Panel for actions and layout.
- HealthBar with accessible progress values.
- PetAvatar with original CSS placeholder creatures and idle animation.
- SkillCard with keyboard focus and selected state.
- Seven categories fetched from `/api/skills`, plus `/api/health` and `POST /api/questions`.
- Responsive arena preview with explicit loading/error states.

## Basic checks

```sh
pnpm build
pnpm format:check
uv run pytest
```

`pnpm build` typechecks and builds the frontend into `public/`. `pnpm format` formats frontend/configuration files and Python. The tests mock the model call and do not require credentials.

## One deployment on Vercel

Import this repository with the repository root as Root Directory. `vercel.json` selects the Container framework preset. Vercel builds the root Dockerfile and runs one HTTP server serving React and `/api` together. The container listens on port 80 by default, matching Vercel routing. If you override PORT, set the matching environment variable in Vercel.

The Container runtime is currently beta. See [Vercel container deployment guidance](https://vercel.com/kb/guide/does-vercel-support-docker-deployments).

After deployment, check `/`, `/api/health`, `/api/skills`, and `/battle/preview`. Make sure deployment protection allows public access for the hackathon submission. No deployment has been performed yet.

## One Docker container

```sh
docker build -t codex-arena .
docker run --rm -p 8000:80 codex-arena
```

Open http://localhost:8000. The multi-stage image builds React, installs Python dependencies with uv, and serves both with Uvicorn as a non-root user. The `PORT` environment variable defaults to 80.

The same image can also run on other container hosts. The app works without a separate frontend host or CORS configuration.

## Integration boundaries

The practice prototype returns answer keys to the client for inspection. Multiplayer game answers remain on the server. Shared games use Redis and expire after inactivity; polling delivers updates to clients. Add durable storage if a leaderboard is needed.

Pet artwork is presentation only; importing an avatar does not import a model, conversation, or account credentials. Replace PetAvatar with original or licensed sprites when ready.

## Credits

Created during the DevDay Community Hackathon in London on 1 November 2026. React/TypeScript scaffold generated using create-vite. Codex helped write the React primitives, FastAPI routes, and deployment configuration. The included pets are original CSS placeholders. No Pokémon assets are bundled. DM Sans and Space Grotesk are loaded from Google Fonts with system fallbacks. Dependencies retain their respective licenses.

## Generate a question

With the server running and an API key configured:

```sh
curl -X POST http://localhost:5001/api/questions \
  -H 'Content-Type: application/json' \
  -d '{"category":"python"}'
```

The response includes `category`, `question`, four options with IDs A–D, and `correct_answer`. The API validates the response structure, but generated answers should be reviewed for accuracy. FastAPI's interactive API documentation is available at `/docs`. For Docker, pass credentials with `--env-file .env`.

## Game API

Set `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` to an Upstash Redis database in Vercel and in the local environment. The preview still works without them; game endpoints return 503 without storage. Games expire after one hour without activity.

- `POST /api/games` with `{"category":"python"}` creates a game and returns its code and player token.
- `POST /api/games/{code}/join` with `{"category":"web"}` joins it and returns the second token. Players must choose different categories.
- `GET /api/games/{code}` returns the current state. Send `Authorization: Bearer <player token>` and poll approximately once per second.
- `POST /api/games/{code}/answers` with the same authorization and `{"round":1,"answer":0}` submits a zero-based option index.

Round deadlines and `server_time` are Unix timestamps in seconds. Show a local countdown using their difference; the server rejects late answers. A poll or other request resolves an expired round and starts the next one. `history` reports correctness for each player, with `null` for a timeout. `winner` is a zero-based player index or `null` for a draw. Player tokens are credentials and should be kept private. The current frontend is still an arena preview; these endpoints are ready for a game client.

Run backend tests with `uv run python -m unittest -v`.
