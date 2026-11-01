import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

import game
from test_game import MemoryStore, generated_questions, start_playing


def room():
    store = MemoryStore()
    first = game.create_game(store, "maths")
    second = game.join_game(store, first["code"], "geography")
    return store, first["code"], [first["token"], second["token"]]


def test_both_ready_generates_once_and_explicit_start():
    store, code, tokens = room()
    with patch("game.generate_questions", side_effect=generated_questions) as generate:
        with pytest.raises(game.GameError):
            start_playing(store, code, tokens[0])
        state = game.ready_game(store, code, tokens[0])
        assert state["phase"] == "waiting"
        generate.assert_not_called()
        with ThreadPoolExecutor(max_workers=2) as executor:
            list(
                executor.map(lambda token: game.ready_game(store, code, token), tokens)
            )
        assert generate.call_count == 1
        state = game.get_game(store, code, tokens[0])
        assert state["phase"] == "ready"
        assert "question" not in state and "deadline" not in state
        started = start_playing(store, code, tokens[1])
        assert started["phase"] == "playing"
        assert started["deadline"] - started["server_time"] == 30
        with pytest.raises(game.GameError):
            start_playing(store, code, "bad token")


def test_bot_completes_five_rounds_without_second_client():
    store = MemoryStore()
    first = game.create_game(store, "maths", mode="bot")
    code, token = first["code"], first["token"]
    with patch("game.generate_questions", side_effect=generated_questions):
        state = game.ready_game(store, code, token)
    assert state["phase"] == "ready"
    assert state["players"][1]["bot"] is True
    with patch("game.time.time", return_value=100):
        start_playing(store, code, token)
    for round_number in range(1, 6):
        raw = json.loads(store.get(code))
        with patch("game.time.time", return_value=raw["deadline"] - 29):
            result = game.answer_game(store, code, token, round_number, 0)
        if round_number == 1:
            assert [p["score"] for p in result["players"]] == [0, 0]
        with patch("game.time.time", return_value=raw["deadline"] - 28):
            state = game.get_game(store, code, token)
        assert state["history"][-1]["answers"][0] is True
        assert state["history"][-1]["answers"][1] is not None
    assert state["phase"] == "finished"
    assert len(state["history"]) == 5


def test_stuck_generation_can_be_retried():
    store, code, tokens = room()
    value = json.loads(store.get(code))
    value.update(phase="generating", generation="abandoned", generation_deadline=0)
    for player in value["players"]:
        player["ready"] = True
    store.games[code] = json.dumps(value)
    with patch("game.generate_questions", side_effect=generated_questions):
        assert game.ready_game(store, code, tokens[0])["phase"] == "ready"
