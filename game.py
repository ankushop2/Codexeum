import json
import os
import secrets
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from question_generator import generate_questions

CATEGORIES = ("debugging", "python", "javascript", "logic", "web", "data", "security")
TTL = 3600
CAS = "if redis.call('GET', KEYS[1]) == ARGV[1] then redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[3]); return 1 else return 0 end"


class StoreUnavailable(Exception):
    pass


class GameError(Exception):
    def __init__(self, message, status):
        self.message, self.status = message, status


class RedisStore:
    def command(self, *args):
        url = os.environ.get("UPSTASH_REDIS_REST_URL")
        token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
        if not url or not token:
            raise StoreUnavailable()
        request = Request(
            url,
            data=json.dumps(args).encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=5) as response:
                result = json.load(response)
            if "error" in result:
                raise StoreUnavailable()
            return result["result"]
        except (URLError, OSError, ValueError, KeyError):
            raise StoreUnavailable() from None

    def create(self, code, game):
        return (
            self.command("SET", "game:" + code, json.dumps(game), "EX", TTL, "NX")
            == "OK"
        )

    def get(self, code):
        return self.command("GET", "game:" + code)

    def replace(self, code, old, game):
        return (
            self.command("EVAL", CAS, 1, "game:" + code, old, json.dumps(game), TTL)
            == 1
        )


def player(category):
    return {"token": secrets.token_urlsafe(32), "category": category, "score": 0}


def create_game(store, category):
    validate_category(category)
    for _ in range(10):
        code = "".join(
            secrets.choice("23456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(6)
        )
        first = player(category)
        game = {
            "code": code,
            "players": [first],
            "phase": "waiting",
            "round": 0,
            "answers": {},
            "history": [],
        }
        if store.create(code, game):
            return {"code": code, "token": first["token"]}
    raise GameError("Could not create a game; try again", 503)


def validate_category(category):
    if not isinstance(category, str) or category not in CATEGORIES:
        raise GameError("Invalid category", 400)


def advance(game, now):
    game["history"].append(
        {
            "round": game["round"] + 1,
            "category": game["questions"][game["round"]]["category"],
            "answers": [
                game["answers"].get(str(i), {}).get("correct") for i in range(2)
            ],
        }
    )
    game["round"] += 1
    game["answers"] = {}
    if game["round"] == 5:
        game["phase"] = "finished"
        game["deadline"] = None
    else:
        game["deadline"] = now + 10


def update(store, code, action):
    for _ in range(20):
        raw = store.get(code)
        if raw is None:
            raise GameError("Game not found or expired", 404)
        game = json.loads(raw)
        now = time.time()
        if game["phase"] == "playing" and now >= game["deadline"]:
            advance(game, now)
        result = action(game, now)
        if store.replace(code, raw, game):
            return result(game, now)
    raise GameError("Game is busy; retry", 409)


def join_game(store, code, category):
    validate_category(category)

    raw = store.get(code)
    if raw is None:
        raise GameError("Game not found or expired", 404)
    existing = json.loads(raw)
    if existing["phase"] != "waiting":
        raise GameError("Game is full", 409)
    first_category = existing["players"][0]["category"]
    if first_category == category:
        raise GameError("Choose a different category", 400)
    other = secrets.choice(
        [c for c in CATEGORIES if c not in (category, first_category)]
    )
    questions = generate_questions(first_category, category, other)
    secrets.SystemRandom().shuffle(questions)

    def action(game, now):
        if game["phase"] != "waiting":
            raise GameError("Game is full", 409)
        second = player(category)
        game["players"].append(second)
        game["questions"] = questions
        game["phase"] = "playing"
        game["deadline"] = now + 10
        return lambda game, now: {"code": code, "token": second["token"]}

    return update(store, code, action)


def identify(game, token):
    for i, p in enumerate(game["players"]):
        if isinstance(token, str) and secrets.compare_digest(p["token"], token):
            return i
    raise GameError("Invalid player token", 401)


def view(game, now, index):
    result = {
        "code": game["code"],
        "phase": game["phase"],
        "players": [
            {
                "category": p["category"],
                "score": p["score"]
                - (
                    (
                        2
                        if p["category"] == game["questions"][game["round"]]["category"]
                        else 5
                    )
                    if game["phase"] == "playing"
                    and game["answers"].get(str(i), {}).get("correct")
                    else 0
                ),
            }
            for i, p in enumerate(game["players"])
        ],
        "you": index,
        "server_time": now,
        "history": game["history"],
    }
    if game["phase"] == "playing":
        question = game["questions"][game["round"]]
        result.update(
            {
                "round": game["round"] + 1,
                "deadline": game["deadline"],
                "question": {k: question[k] for k in ("category", "prompt", "options")},
                "answered": str(index) in game["answers"],
            }
        )
    if game["phase"] == "finished":
        scores = [p["score"] for p in game["players"]]
        result["winner"] = None if scores[0] == scores[1] else scores.index(max(scores))
    return result


def get_game(store, code, token):
    def action(game, now):
        index = identify(game, token)
        return lambda game, now: view(game, now, index)

    return update(store, code, action)


def answer_game(store, code, token, round_number, answer):
    def action(game, now):
        index = identify(game, token)
        if (
            game["phase"] != "playing"
            or type(round_number) is not int
            or round_number != game["round"] + 1
        ):
            raise GameError("Round is no longer active", 409)
        if str(index) in game["answers"]:
            raise GameError("Already answered this round", 409)
        question = game["questions"][game["round"]]
        if type(answer) is not int or not 0 <= answer < len(question["options"]):
            raise GameError("Invalid answer", 400)
        correct = answer == question["answer"]
        if correct:
            game["players"][index]["score"] += (
                2 if game["players"][index]["category"] == question["category"] else 5
            )
        game["answers"][str(index)] = {"correct": correct}
        if len(game["answers"]) == 2:
            advance(game, now)
        return lambda game, now: view(game, now, index)

    return update(store, code, action)
