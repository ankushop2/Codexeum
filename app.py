from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

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
