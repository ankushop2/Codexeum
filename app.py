from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from werkzeug.exceptions import HTTPException

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
