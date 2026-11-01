from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from game import (
    GameError,
    RedisStore,
    StoreUnavailable,
    answer_game,
    create_game,
    get_game,
    join_game,
)

PUBLIC = Path(__file__).parent / "public"
app = Flask(__name__, static_folder=None)

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


@app.get("/")
@app.get("/<path:path>")
def frontend(path=""):
    if path == "api" or path.startswith("api/"):
        return jsonify(error="API route not found"), 404
    if not (PUBLIC / "index.html").exists():
        return jsonify(error="Frontend not built. Run pnpm build."), 503
    if path and (PUBLIC / path).is_file():
        return send_from_directory(PUBLIC, path)
    if path and "." in path.rsplit("/", 1)[-1]:
        return jsonify(error="Asset not found"), 404
    return send_from_directory(PUBLIC, "index.html")


@app.errorhandler(HTTPException)
def http_error(error):
    if error.code == 405 or not error.description:
        return jsonify(error=error.name), error.code
    return jsonify(error=error.name), error.code


store = RedisStore()


def body():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise GameError("Expected a JSON object", 400)
    return value


def token():
    return request.headers.get("Authorization", "").removeprefix("Bearer ")


@app.errorhandler(GameError)
def game_error(error):
    return jsonify(error=error.message), error.status


@app.errorhandler(StoreUnavailable)
def store_error(error):
    return jsonify(error="Game storage unavailable"), 503


@app.post("/api/games")
def create():
    return jsonify(create_game(store, body().get("category"))), 201


@app.post("/api/games/<code>/join")
def join(code):
    return jsonify(join_game(store, code.upper(), body().get("category")))


@app.get("/api/games/<code>")
def state(code):
    response = jsonify(get_game(store, code.upper(), token()))
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/api/games/<code>/answers")
def answer(code):
    data = body()
    return jsonify(
        answer_game(store, code.upper(), token(), data.get("round"), data.get("answer"))
    )
