import base64
import binascii
import json
import os
import re
import secrets
import struct
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from question_generator import GenerationError, generate_questions

CATEGORIES = ("geography", "art", "maths", "biology", "history", "music", "science")
BOT_DIFFICULTIES = {"easy": 2, "med": 3, "hard": 4}
ROUND_SECONDS = 30
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
        entries = []
        result = None
        if game["phase"] == "finished" and json.loads(old)["phase"] != "finished":
            result = {
                "room": code,
                "completed_at": time.time(),
                "players": [
                    {
                        "nickname": p["nickname"],
                        "pet": p["pet"]["name"],
                        "score": p["score"],
                        "bot": p.get("bot", False),
                    }
                    for p in game["players"]
                ],
                "rounds": game["history"],
            }
            scores = [p["score"] for p in game["players"]]
            for p in game["players"]:
                if not p.get("bot"):
                    entries.append(
                        {
                            "key": p["nickname"].strip().casefold(),
                            "nickname": p["nickname"],
                            "pet": p["pet"]["name"],
                            "score": p["score"],
                            "subjects": {
                                category: {
                                    "attempts": sum(
                                        r["category"] == category
                                        for r in game["history"]
                                    ),
                                    "correct": sum(
                                        r["category"] == category
                                        and r["answers"][game["players"].index(p)]
                                        is True
                                        for r in game["history"]
                                    ),
                                }
                                for category in CATEGORIES
                            },
                            "win": int(
                                p["score"] == max(scores) and scores[0] != scores[1]
                            ),
                        }
                    )
        script = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[3])
if ARGV[5] ~= 'null' then
  redis.call('XADD', KEYS[4], '*', 'result', ARGV[5])
end
for _, entry in ipairs(cjson.decode(ARGV[4])) do
  local raw = redis.call('HGET', KEYS[3], entry.key)
  local row = raw and cjson.decode(raw) or {points=0, games=0, wins=0}
  row.nickname = entry.nickname
  row.pet = entry.pet
  row.points = row.points + entry.score
  row.games = row.games + 1
  row.wins = row.wins + entry.win
  row.subjects = row.subjects or {}
  for category, counts in pairs(entry.subjects) do
    local subject = row.subjects[category] or {attempts=0, correct=0}
    subject.attempts = subject.attempts + counts.attempts
    subject.correct = subject.correct + counts.correct
    row.subjects[category] = subject
  end
  redis.call('HSET', KEYS[3], entry.key, cjson.encode(row))
  redis.call('ZADD', KEYS[2], row.points, entry.key)
end
return 1
"""
        return (
            self.command(
                "EVAL",
                script,
                4,
                "game:" + code,
                "arena:leaders",
                "arena:profiles",
                "arena:results",
                old,
                json.dumps(game),
                TTL,
                json.dumps(entries),
                json.dumps(result),
            )
            == 1
        )

    def progress(self, nickname):
        raw = self.command("HGET", "arena:profiles", nickname.strip().casefold())
        return json.loads(raw).get("subjects", {}) if raw else {}

    def leaderboard(self):
        names = self.command("ZREVRANGE", "arena:leaders", 0, 19)
        if not names:
            return []
        records = self.command("HMGET", "arena:profiles", *names)
        return [
            {"rank": index + 1, **json.loads(record)}
            for index, record in enumerate(records)
            if record
        ]


def appearance(value):
    if value is None:
        return {"nickname": "TRAINER", "pet": {"name": "BYTE", "color": "#aaa0e8"}}
    if not isinstance(value, dict):
        raise GameError("Invalid trainer appearance", 400)
    nickname = value.get("nickname", "TRAINER")
    pet = value.get("pet", {})
    if (
        not isinstance(nickname, str)
        or not 1 <= len(nickname.strip()) <= 20
        or not isinstance(pet, dict)
    ):
        raise GameError("Invalid trainer appearance", 400)
    name, color = pet.get("name", "BYTE"), pet.get("color", "#aaa0e8")
    if (
        not isinstance(name, str)
        or not 1 <= len(name) <= 20
        or not isinstance(color, str)
        or not re.fullmatch(r"#[0-9a-fA-F]{6}", color)
    ):
        raise GameError("Invalid pet appearance", 400)
    clean = {"name": name, "color": color}
    image = pet.get("image")
    if image is not None:
        if (
            not isinstance(image, str)
            or len(image) > 100000
            or not image.startswith("data:image/png;base64,")
        ):
            raise GameError("Invalid pet portrait", 400)
        try:
            raw = base64.b64decode(image.split(",", 1)[1], validate=True)
            if (
                len(raw) < 24
                or raw[:8] != b"\x89PNG\r\n\x1a\n"
                or raw[12:16] != b"IHDR"
            ):
                raise ValueError()
            width, height = struct.unpack(">II", raw[16:24])
            if not 1 <= width <= 128 or not 1 <= height <= 128:
                raise ValueError()
        except (ValueError, binascii.Error, struct.error):
            raise GameError("Invalid pet portrait", 400) from None
        clean["image"] = image
    return {"nickname": nickname.strip(), "pet": clean}


def player(category, profile=None):
    return {
        "token": secrets.token_urlsafe(32),
        "category": category,
        "score": 0,
        "ready": False,
        "bot": False,
        **appearance(profile),
    }


def create_game(store, category, profile=None, mode="player", difficulty="med"):
    if mode not in ("player", "bot"):
        raise GameError("Invalid game mode", 400)
    if mode == "bot" and (
        not isinstance(difficulty, str) or difficulty not in BOT_DIFFICULTIES
    ):
        raise GameError("Invalid bot difficulty; choose easy, med or hard", 400)
    validate_category(category)
    profile = appearance(profile)
    for _ in range(10):
        code = "".join(
            secrets.choice("23456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(6)
        )
        first = player(category, profile)
        game = {
            "code": code,
            "players": [first],
            "phase": "waiting",
            "round": 0,
            "answers": {},
            "history": [],
        }
        if mode == "bot":
            opponent = player(
                secrets.choice([c for c in CATEGORIES if c != category]),
                {"nickname": "BOT", "pet": {"name": "GLITCH", "color": "#9bc6a1"}},
            )
            opponent.update(bot=True, ready=True)
            game["players"].append(opponent)
            correct_count = BOT_DIFFICULTIES[difficulty] + secrets.choice((-1, 0, 1))
            game["bot_difficulty"] = difficulty
            game["bot_correct_rounds"] = secrets.SystemRandom().sample(
                range(5), correct_count
            )
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
            "correct_answer": game["questions"][game["round"]]["options"][
                game["questions"][game["round"]]["answer"]
            ],
            "answers": [
                game["answers"].get(str(i), {}).get("correct") for i in range(2)
            ],
            "sources": [
                game["answers"].get(str(i), {}).get("source") for i in range(2)
            ],
            "points": [game["answers"].get(str(i), {}).get("points") for i in range(2)],
        }
    )
    game["round"] += 1
    game["answers"] = {}
    if game["round"] == 5:
        game["phase"] = "finished"
        game["deadline"] = None
    else:
        begin_round(game, now)


def update(store, code, action):
    for _ in range(20):
        raw = store.get(code)
        if raw is None:
            raise GameError("Game not found or expired", 404)
        game = json.loads(raw)
        now = time.time()
        tick(game, now)
        result = action(game, now)
        if store.replace(code, raw, game):
            return result(game, now)
    raise GameError("Game is busy; retry", 409)


def join_game(store, code, category, profile=None):
    validate_category(category)
    profile = appearance(profile)

    def action(game, now):
        if game["phase"] != "waiting" or len(game["players"]) != 1:
            raise GameError("Game is full", 409)
        if game["players"][0]["category"] == category:
            raise GameError("Choose a different category", 400)
        second = player(category, profile)
        game["players"].append(second)
        return lambda game, now: {"code": code, "token": second["token"]}

    return update(store, code, action)


def ready_game(store, code, token):
    generation = secrets.token_urlsafe(16)

    def claim(game, now):
        index = identify(game, token)
        if game["phase"] == "generating" and now >= game["generation_deadline"]:
            game["phase"] = "waiting"
        if game["phase"] != "waiting":
            return lambda game, now: (False, index, game)
        game["players"][index]["ready"] = True
        generate = len(game["players"]) == 2 and all(
            p.get("ready", False) for p in game["players"]
        )
        if generate:
            game.update(
                phase="generating", generation=generation, generation_deadline=now + 90
            )
        return lambda game, now: (generate, index, game)

    generate, index, snapshot = update(store, code, claim)
    if not generate:
        return view(snapshot, time.time(), index)
    try:
        first, second = [p["category"] for p in snapshot["players"]]
        other = secrets.choice([c for c in CATEGORIES if c not in (first, second)])
        questions = generate_questions(first, second, other)
        secrets.SystemRandom().shuffle(questions)
    except (GenerationError, StoreUnavailable):

        def reset(game, now):
            if game.get("generation") == generation and game["phase"] == "generating":
                game["phase"] = "waiting"
            return lambda game, now: None

        update(store, code, reset)
        raise

    def finish(game, now):
        if game.get("generation") != generation or game["phase"] != "generating":
            raise GameError("Question generation was replaced; refresh the room", 409)
        game.update(questions=questions, phase="ready")
        return lambda game, now: view(game, now, index)

    return update(store, code, finish)


def start_game(store, code, token):
    def action(game, now):
        index = identify(game, token)
        if game["phase"] == "ready":
            game["phase"] = "playing"
            begin_round(game, now)
        elif game["phase"] != "playing":
            raise GameError("Questions are not ready", 409)
        return lambda game, now: view(game, now, index)

    return update(store, code, action)


def begin_round(game, now):
    game["deadline"] = now + ROUND_SECONDS
    if any(p.get("bot") for p in game["players"]):
        game["bot_due"] = now + 2
        question = game["questions"][game["round"]]
        if "bot_correct_rounds" not in game:
            game["bot_answer"] = secrets.randbelow(len(question["options"]))
        elif game["round"] in game["bot_correct_rounds"]:
            game["bot_answer"] = question["answer"]
        else:
            game["bot_answer"] = secrets.choice(
                [
                    index
                    for index in range(len(question["options"]))
                    if index != question["answer"]
                ]
            )


def record_answer(game, index, answer, source="trainer"):
    question = game["questions"][game["round"]]
    correct = answer == question["answer"]
    points = (5 if source == "trainer" else 2) if correct else 0
    game["players"][index]["score"] += points
    game["answers"][str(index)] = {
        "correct": correct,
        "source": source,
        "points": points,
    }


def tick(game, now):
    if game["phase"] == "generating" and now >= game["generation_deadline"]:
        game["phase"] = "waiting"
    if game["phase"] != "playing":
        return
    if game.get("bot_due", float("inf")) <= now:
        for index, p in enumerate(game["players"]):
            if p.get("bot") and str(index) not in game["answers"]:
                record_answer(game, index, game["bot_answer"], "bot")
    if now >= game["deadline"] or len(game["answers"]) == 2:
        advance(game, now)


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
                "ready": p.get("ready", False),
                "bot": p.get("bot", False),
                "nickname": p.get("nickname", "TRAINER"),
                "pet": p.get("pet", {"name": "BYTE", "color": "#aaa0e8"}),
                "score": p["score"]
                - (
                    (
                        game["answers"][str(i)].get(
                            "points",
                            2
                            if p["category"]
                            == game["questions"][game["round"]]["category"]
                            else 5,
                        )
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
    if "bot_difficulty" in game:
        result["bot_difficulty"] = game["bot_difficulty"]
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


def answer_game(store, code, token, round_number, answer, source="trainer"):
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
        if source not in ("trainer", "pet", "team"):
            raise GameError("Invalid answer source", 400)
        record_answer(game, index, answer, source)
        if len(game["answers"]) == 2:
            advance(game, now)
        return lambda game, now: view(game, now, index)

    return update(store, code, action)
