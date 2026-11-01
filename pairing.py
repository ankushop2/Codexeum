"""Five-minute, single-use connection codes for an existing player seat."""

import json
import re
import secrets

from game import GameError, identify, update

PAIR_TTL = 300
CONSUME = "local v = redis.call('GET', KEYS[1]); if v then redis.call('DEL', KEYS[1]); end; return v"


def create_pairing(store, code, token):
    def check(game, now):
        identify(game, token)
        if game["phase"] == "finished":
            raise GameError("This match has finished", 409)
        return lambda game, now: None

    update(store, code, check)
    for _ in range(10):
        pair = "P-" + "".join(
            secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(10)
        )
        if (
            store.command(
                "SET",
                "pair:" + pair,
                json.dumps({"code": code, "token": token}),
                "EX",
                PAIR_TTL,
                "NX",
            )
            == "OK"
        ):
            return {"pairing_code": pair, "expires_in": PAIR_TTL}
    raise GameError("Could not create pairing code; retry", 503)


def redeem_pairing(store, value):
    if not isinstance(value, str) or not re.fullmatch(r"P-[A-Z2-9]{10}", value.upper()):
        raise GameError("Invalid pairing code", 400)
    raw = store.command("EVAL", CONSUME, 1, "pair:" + value.upper())
    if raw is None:
        raise GameError("Pairing code expired or already used", 404)
    session = json.loads(raw)

    def connect(game, now):
        index = identify(game, session["token"])
        if game["phase"] == "finished":
            raise GameError("This match has finished", 409)
        game["players"][index]["controller"] = "codex"
        return lambda game, now: session

    return update(store, session["code"], connect)
