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
