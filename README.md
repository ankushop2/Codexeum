# 🏛️ Codexeum

**Learn new things. Team up with your pet. Have fun.**

Codexeum is a retro quiz game for curious kids. Pick a pet, explore subjects like maths, art and biology, and play five quick rounds against a friend or the computer. Stuck? Ask your pet for help!

## How to play

1. Choose a starter pet or import your own Codex pet.
2. Enter a nickname and pick your pet’s subject.
3. Play with a friend using a room code, or choose the computer.
4. Ready up, start the game and answer five questions—30 seconds each.
5. Review what you learned, explore practice cards and see your pet climb the leaderboard.

**Correct answer:** 5 points on your own, or 2 after pet advice. Wrong answers earn 0. You always choose the final answer.

Pet help is available outside its chosen subject. The learning dashboard shows your accuracy by subject, while the leaderboard adds up points from completed games. Use the same nickname to keep your progress. Nicknames are public; people using the same name share a record.

To import a pet, choose its folder containing `spritesheet.png` (or `.webp`) and `pet-record.json`.

**Coming next:** coding challenges for adult learners and developers.

## Run locally

You need Node.js 24, pnpm, uv, Python 3.12, an OpenAI API key and an Upstash Redis database.

```sh
pnpm install --frozen-lockfile
uv sync --python 3.12
cp .env.example .env
```

Fill in these values in `.env`:

```dotenv
OPENAI_API_KEY=your_key
UPSTASH_REDIS_REST_URL=your_url
UPSTASH_REDIS_REST_TOKEN=your_token
```

Then start the app:

```sh
pnpm dev
```

Open [localhost:5173](http://localhost:5173). API docs: [localhost:5001/docs](http://localhost:5001/docs).

React powers the interface; FastAPI handles the game. OpenAI generates questions and pet advice. Redis stores rooms, rankings, learning progress and completed-match results. Pet advice uses the OpenAI API, not your personal Codex session. AI-generated questions and advice can make mistakes.

Keep credentials in `.env` and out of Git. Imported pet names and small portraits are shared with your opponent.

### Docker

```sh
docker build -t codexeum .
docker run --rm --env-file .env -p 8000:80 codexeum
```

Open [localhost:8000](http://localhost:8000).

## Built with Codex

Built during the DevDay Community Hackathon in London on 1 November 2026. One concrete example: Codex implemented the pet-help flow and scoring, then updated the interface to distinguish independent answers from assisted ones.

The app started with create-vite. It uses React, FastAPI, the OpenAI SDK and Upstash Redis. Starter pets and the pixel Colosseum are project artwork; imported pets belong to their creators. The pixel Codex mark is a stylised rendition of the Codex logo. Fonts come from Google Fonts. Dependencies retain their own licences.

## Codexeum terminal arena and skill

The terminal arena recreates the facing-pet field, question panel, narration, countdown, round history and result screen using terminal colors and image-to-character rendering. It connects to the same FastAPI rooms as the website. Local Codex answers automatically through a dedicated ephemeral App Server conversation; A–D submits a human answer, Space toggles autoplay, and Q exits. READY prepares questions; START BATTLE begins the clock. Exiting does not pause a running server match.

```sh
uv sync --extra tui
uv run --extra tui python -m codexeum new --url http://localhost:5001
uv run --extra tui python -m codexeum ABC123 --url https://YOUR-DEPLOYMENT
```

Supply `--pet /path/to/pet-folder` or `--pet /path/to/image.png` to use your pet; the first idle frame is used for v1/v2 sheets. A single installed custom pet under `~/.codex/pets` is detected automatically. Built-in Codex pet assets and the current desktop selection are not exposed through a verified public API; when no artwork is available, the TUI uses a text cat. `CODEXEUM_PET`, `CODEXEUM_NICKNAME`, `CODEXEUM_URL`, `CODEXEUM_MODEL`, and `CODEXEUM_CODEX_BIN` can set local defaults. The client finds Codex on PATH or in the macOS desktop app bundle and uses its existing sign-in. No OpenAI key is sent to the game server by the terminal client.

To connect an existing browser player, click **CONNECT MY CODEX** in the room and use the `P-` code in place of `ABC123`. Pairing codes expire after five minutes and can be redeemed once. They grant access to that player seat, so keep them private. Room codes join a new seat. Browser and terminal share answer locking; the first accepted answer wins.

The skill source is `skills/codexeum`. Install it for this checkout:

```sh
mkdir -p ~/.agents/skills
ln -s "$PWD/skills/codexeum" ~/.agents/skills/codexeum
```

In the desktop app, enabled skills appear in the slash menu: select **codexeum**, then supply `new`, a room code, or a pairing code. `$codexeum new` is the explicit skill form supported across Codex surfaces. Stock Codex CLI does not document arbitrary bare `/codexeum` registration from a skill; use `$codexeum new` or `/skills` there. This project does not modify the Codex executable.

The skill launches a separate visible terminal via `scripts/launch_codexeum.py`. You can also launch it directly:

```sh
python3 scripts/launch_codexeum.py new --url https://YOUR-DEPLOYMENT
```

Terminal dependencies are optional and are not installed in the production Docker image. The server still needs its OpenAI and Redis settings. Tests use a mocked Codex protocol and in-memory game storage; a real match additionally needs a reachable server and signed-in local Codex.
