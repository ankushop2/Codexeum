from pathlib import Path
from typing import Annotated, Any
import os

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from openai import APIError, OpenAI

from game import (
    GameError,
    RedisStore,
    StoreUnavailable,
    answer_game,
    create_game,
    get_game,
    join_game,
)
from question_generator import ConfigurationError, GenerationError

load_dotenv()
PUBLIC = Path(__file__).parent / "public"
app = FastAPI(title="Codex Arena API")

SKILLS = [
    {"id": "debugging", "name": "Debugging", "symbol": "⌘"},
    {"id": "python", "name": "Python", "symbol": "Py"},
    {"id": "javascript", "name": "JavaScript", "symbol": "JS"},
    {"id": "logic", "name": "Logic", "symbol": "◇"},
    {"id": "web", "name": "Web", "symbol": "◎"},
    {"id": "data", "name": "Data", "symbol": "▥"},
    {"id": "security", "name": "Security", "symbol": "⛨"},
]


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "codex-pet-battle"}


@app.get("/api/skills")
def skills():
    return {"skills": SKILLS}


store = RedisStore()


@app.exception_handler(GameError)
async def game_error(request: Request, error: GameError):
    return JSONResponse({"error": error.message}, status_code=error.status)


@app.exception_handler(ConfigurationError)
async def configuration_error(request: Request, error: ConfigurationError):
    return JSONResponse({"error": str(error)}, status_code=503)


@app.exception_handler(GenerationError)
async def generation_error(request: Request, error: GenerationError):
    return JSONResponse({"error": str(error)}, status_code=502)


@app.exception_handler(StoreUnavailable)
async def store_error(request: Request, error: StoreUnavailable):
    return JSONResponse({"error": "Game storage unavailable"}, status_code=503)


def body(value):
    if not isinstance(value, dict):
        raise GameError("Expected a JSON object", 400)
    return value


def token(request: Request):
    return request.headers.get("Authorization", "").removeprefix("Bearer ")


@app.post("/api/games", status_code=201)
def create(data: Annotated[Any, Body()] = None):
    data = body(data)
    return create_game(store, data.get("category"), data.get("profile"))


@app.post("/api/games/{code}/join")
def join(code: str, data: Annotated[Any, Body()] = None):
    data = body(data)
    return join_game(store, code.upper(), data.get("category"), data.get("profile"))


@app.get("/api/games/{code}")
def state(code: str, request: Request):
    return JSONResponse(
        get_game(store, code.upper(), token(request)),
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/games/{code}/answers")
def answer(code: str, request: Request, data: Annotated[Any, Body()] = None):
    data = body(data)
    return answer_game(
        store, code.upper(), token(request), data.get("round"), data.get("answer")
    )


@app.post("/api/games/{code}/pet")
def ask_pet(code: str, request: Request, data: Annotated[Any, Body()] = None):
    data = body(data)
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 500:
        raise GameError("Enter a prompt of up to 500 characters", 400)
    game = get_game(store, code.upper(), token(request))
    if (
        game["phase"] != "playing"
        or game["round"] != data.get("round")
        or game["answered"]
    ):
        raise GameError("Round is no longer active", 409)
    if not os.getenv("OPENAI_API_KEY"):
        raise ConfigurationError("OPENAI_API_KEY is not configured on the server.")
    question = game["question"]
    options = "\n".join(
        f"{chr(65 + i)}. {option}" for i, option in enumerate(question["options"])
    )
    try:
        response = OpenAI(timeout=7.0, max_retries=0).responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            instructions="You are a player's friendly battle pet. Help with the current quiz question. Be brief, suggest an option when useful, and never claim you submitted an answer. The player chooses the answer.",
            input=f"Question: {question['prompt']}\n{options}\n\nPlayer's prompt: {prompt.strip()}",
            max_output_tokens=150,
        )
    except APIError as exc:
        raise GenerationError(
            "Your pet couldn't respond. Try answering yourself."
        ) from exc
    return {
        "round": game["round"],
        "reply": response.output_text or "I couldn't think of an answer. You choose!",
    }


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    if path == "api" or path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    index = PUBLIC / "index.html"
    if not index.is_file():
        raise HTTPException(
            status_code=503, detail="Frontend not built. Run pnpm build."
        )
    candidate = (PUBLIC / path).resolve()
    if candidate.is_relative_to(PUBLIC.resolve()) and candidate.is_file():
        return FileResponse(candidate)
    if path and "." in path.rsplit("/", 1)[-1]:
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(index)
