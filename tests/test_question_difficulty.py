from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app
import game
from test_game import MemoryStore, generated_questions


def test_unified_code_category_can_play_other_subjects(monkeypatch):
    store = MemoryStore()
    monkeypatch.setattr(app, "store", store)
    client = TestClient(app.app)
    skills = client.get("/api/skills").json()["skills"]
    assert len(skills) == 8
    assert [skill["name"] for skill in skills if skill["id"] == "code"] == ["Code"]
    assert not {"python", "javascript", "debugging"}.intersection(
        skill["id"] for skill in skills
    )
    host = client.post(
        "/api/games", json={"category": "code", "question_difficulty": "hard"}
    ).json()
    guest = client.post(
        f"/api/games/{host['code']}/join",
        json={"category": "science", "question_difficulty": "easy"},
    )
    assert guest.status_code == 200
    with patch("game.generate_questions", side_effect=generated_questions) as generate:
        game.ready_game(store, host["code"], host["token"])
        state = game.ready_game(store, host["code"], guest.json()["token"])
    assert state["question_difficulty"] == "hard"
    first, second, other, difficulty = generate.call_args.args
    assert (first, second, difficulty) == ("code", "science", "hard")
    assert other in game.CATEGORIES and other not in (first, second)


def test_question_difficulty_is_independent_of_bot_difficulty():
    store = MemoryStore()
    session = game.create_game(
        store, "code", mode="bot", difficulty="easy", question_difficulty="hard"
    )
    state = game.get_game(store, session["code"], session["token"])
    assert state["question_difficulty"] == "hard"
    assert state["bot_difficulty"] == "easy"
    default = game.create_game(store, "maths")
    assert (
        game.get_game(store, default["code"], default["token"])["question_difficulty"]
        == "med"
    )


@pytest.mark.parametrize("invalid", [None, [], "a-level", "impossible"])
def test_invalid_question_difficulty_leaves_store_unchanged(invalid):
    store = MemoryStore()
    with pytest.raises(game.GameError):
        game.create_game(store, "code", question_difficulty=invalid)
    assert store.games == {}


def test_previous_coding_progress_is_combined_into_code():
    import json

    store = game.RedisStore()
    with patch.object(
        store,
        "command",
        return_value=json.dumps(
            {
                "subjects": {
                    "python": {"attempts": 2, "correct": 1},
                    "javascript": {"attempts": 3, "correct": 2},
                    "code": {"attempts": 1, "correct": 1},
                }
            }
        ),
    ):
        assert store.progress("trainer") == {"code": {"attempts": 6, "correct": 4}}
