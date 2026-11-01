import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app
import game
from test_game import MemoryStore, start_playing


def questions(first, second, other, difficulty="med"):
    return [
        {
            "category": category,
            "prompt": f"Question {i}",
            "options": ["A", "B", "C", "D"],
            "answer": i % 4,
        }
        for i, category in enumerate([first, first, second, second, other])
    ]


@pytest.mark.parametrize(("difficulty", "base"), [("easy", 2), ("med", 3), ("hard", 4)])
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_difficulty_controls_exact_correct_count(difficulty, base, offset):
    store = MemoryStore()
    choose = game.secrets.choice
    with patch(
        "game.secrets.choice",
        side_effect=lambda values: offset if values == (-1, 0, 1) else choose(values),
    ):
        session = game.create_game(store, "maths", mode="bot", difficulty=difficulty)
    code, token = session["code"], session["token"]
    plan = json.loads(store.get(code))["bot_correct_rounds"]
    assert len(plan) == len(set(plan)) == base + offset
    with patch("game.generate_questions", side_effect=questions):
        game.ready_game(store, code, token)
    start_playing(store, code, token)
    for _ in range(5):
        raw = json.loads(store.get(code))
        with patch("game.time.time", return_value=raw["deadline"] - 58):
            state = game.get_game(store, code, token)
            repeated = game.get_game(store, code, token)
            assert state == repeated
            assert state["bot_difficulty"] == difficulty
            assert "bot_correct_rounds" not in state and "bot_answer" not in state
        with patch("game.time.time", return_value=raw["deadline"]):
            state = game.get_game(store, code, token)
    assert state["phase"] == "finished"
    assert sum(round["answers"][1] for round in state["history"]) == base + offset
    assert json.loads(store.get(code))["bot_correct_rounds"] == plan


def test_api_difficulty_validation_and_default(monkeypatch):
    store = MemoryStore()
    monkeypatch.setattr(app, "store", store)
    client = TestClient(app.app)
    for invalid in ("impossible", None, [], True):
        response = client.post(
            "/api/games",
            json={"category": "maths", "mode": "bot", "difficulty": invalid},
        )
        assert response.status_code == 400
        assert not store.games
    response = client.post(
        "/api/games", json={"category": "maths", "mode": "bot", "difficulty": "hard"}
    )
    assert response.status_code == 201
    assert json.loads(store.get(response.json()["code"]))["bot_difficulty"] == "hard"
    session = client.post(
        "/api/games", json={"category": "maths", "mode": "bot"}
    ).json()
    assert json.loads(store.get(session["code"]))["bot_difficulty"] == "med"
    human = client.post("/api/games", json={"category": "maths"}).json()
    assert "bot_correct_rounds" not in json.loads(store.get(human["code"]))
