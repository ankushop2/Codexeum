import argparse
import asyncio
import os
import sys

from .pets import load_pet
from .tui import ArenaApp


def main():
    parser = argparse.ArgumentParser(
        description="Codexeum terminal arena. Create a room with new, join a room, or pair your browser seat."
    )
    parser.add_argument(
        "target", nargs="?", default="new", help="new, room code, or P- pairing code"
    )
    parser.add_argument(
        "--url", default=os.getenv("CODEXEUM_URL", "http://localhost:5001")
    )
    parser.add_argument("--nickname", default=os.getenv("CODEXEUM_NICKNAME", "TRAINER"))
    parser.add_argument(
        "--category",
        default="maths",
        choices=(
            "geography",
            "art",
            "maths",
            "biology",
            "history",
            "music",
            "science",
            "code",
        ),
    )
    parser.add_argument(
        "--question-difficulty",
        choices=("easy", "med", "hard"),
        default="med",
        help="Question difficulty when creating a game",
    )
    parser.add_argument(
        "--pet",
        help="Local Codex pet folder or image; a single installed custom pet is discovered automatically",
    )
    parser.add_argument(
        "--bot", action="store_true", help="Create a new room against the arena bot"
    )
    parser.add_argument(
        "--model",
        default=os.getenv("CODEXEUM_MODEL"),
        help="Optional local Codex model override",
    )
    args = parser.parse_args()
    if not sys.stdin.isatty():
        parser.error(
            "The arena needs an interactive terminal. Use scripts/launch_codexeum.py from a skill to open a terminal window."
        )
    try:
        pet = load_pet(args.pet)
    except (OSError, ValueError) as exc:
        parser.error(f"Could not load pet: {exc}")
    app = ArenaApp(
        args.target,
        args.url,
        pet,
        args.nickname,
        args.category,
        args.bot,
        args.model,
        question_difficulty=args.question_difficulty,
    )

    async def run():
        try:
            await app.run_async()
        finally:
            await app.shutdown()

    asyncio.run(run())


if __name__ == "__main__":
    main()
