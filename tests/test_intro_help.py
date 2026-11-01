import json
from unittest.mock import Mock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI

import app
import game
import question_generator
from test_game import MemoryStore, start_playing


def challenges(first, second, other, difficulty="med"):
    return [
        {
            "category": category,
            "difficulty": "hard" if i in (1, 3) else "standard",
            "prompt": f"Question {i}",
            "options": ["one", "two", "three", "four"],
            "answer": 2,
        }
        for i, category in enumerate([first, first, second, second, other])
    ]


def setup_game():
    store = MemoryStore()
    first = game.create_game(store, "maths")
    second = game.join_game(store, first["code"], "art")
    tokens = [first["token"], second["token"]]
    with patch("game.generate_questions", side_effect=challenges):
        for token in tokens:
            game.ready_game(store, first["code"], token)
    return store, first["code"], tokens


def test_intro_before_clock_and_cannot_skip():
    store, code, tokens = setup_game()
    with patch("game.time.time", return_value=100):
        state = game.start_game(store, code, tokens[0])
        assert state["phase"] == "intro"
        assert state["intro_ends_at"] == 103
        assert "question" not in state and "deadline" not in state
        assert game.start_game(store, code, tokens[1])["intro_ends_at"] == 103
        with pytest.raises(game.GameError):
            game.answer_game(store, code, tokens[0], 1, 0)
    with patch("game.time.time", return_value=103):
        state = game.get_game(store, code, tokens[0])
        assert state["phase"] == "playing"
        assert state["deadline"] == 163


def hard_round(store, code, token):
    start_playing(store, code, token)
    raw = json.loads(store.get(code))
    raw["questions"][0]["difficulty"] = "hard"
    store.games[code] = json.dumps(raw)


def test_elimination_private_persistent_and_scored_as_help():
    store, code, tokens = setup_game()
    hard_round(store, code, tokens[0])
    choose = Mock(return_value=[0, 1])
    assert game.eliminate_options(store, code, tokens[0], 1, choose) == [0, 1]
    assert game.eliminate_options(store, code, tokens[0], 1, choose) == [0, 1]
    choose.assert_called_once()
    assert game.get_game(store, code, tokens[0])["eliminated"] == [0, 1]
    assert game.get_game(store, code, tokens[1])["eliminated"] == []
    with pytest.raises(game.GameError):
        game.answer_game(store, code, tokens[0], 1, 0)
    game.answer_game(store, code, tokens[0], 1, 2, "trainer")
    result = game.answer_game(store, code, tokens[1], 1, 2)
    assert result["history"][0]["points"] == [2, 5]
    assert result["eliminated"] == []


@pytest.mark.parametrize("invalid", [[2, 1], [0, 0], [0, 7], [False, 1]])
def test_invalid_elimination_leaves_options_available(invalid):
    store, code, tokens = setup_game()
    hard_round(store, code, tokens[0])
    with pytest.raises(game.GameError):
        game.eliminate_options(store, code, tokens[0], 1, lambda question: invalid)
    assert game.get_game(store, code, tokens[0])["eliminated"] == []


def test_late_elimination_rejected():
    store, code, tokens = setup_game()
    hard_round(store, code, tokens[0])
    deadline = json.loads(store.get(code))["deadline"]
    with (
        patch("game.time.time", side_effect=[deadline - 1, deadline]),
        pytest.raises(game.GameError),
    ):
        game.eliminate_options(store, code, tokens[0], 1, lambda question: [0, 1])


def test_decisions_http_and_safe_choices(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    def handle(request):
        assert request.url.path == "/v1/decisions"
        body = json.loads(request.content)
        choices = body["questions"][0]["choices"]
        assert len(choices) == 3
        assert all("2" not in choice["value"].split(",") for choice in choices)
        return httpx.Response(
            200,
            json={
                "answers": [
                    {
                        "type": "choice",
                        "name": "eliminate",
                        "choice": choices[0]["value"],
                    }
                ]
            },
        )

    client = OpenAI(
        api_key="test", http_client=httpx.Client(transport=httpx.MockTransport(handle))
    )
    monkeypatch.setattr(question_generator, "OpenAI", lambda **kwargs: client)
    question = challenges("maths", "art", "music")[1]
    assert question_generator.choose_eliminations(question) == [0, 1]


def test_pet_endpoint_hard_question_returns_hint_not_answer(monkeypatch):
    store, code, tokens = setup_game()
    hard_round(store, code, tokens[0])
    monkeypatch.setattr(app, "store", store)
    monkeypatch.setattr(app, "choose_eliminations", lambda question, prompt: [0, 1])
    result = TestClient(app.app).post(
        f"/api/games/{code}/pet",
        headers={"Authorization": "Bearer " + tokens[0]},
        json={"round": 1},
    )
    assert result.status_code == 200
    assert result.json()["eliminated"] == [0, 1]
    assert result.json()["answer"] is None


def test_intro_strip_dimensions_are_validated():
    import base64
    import struct
    import zlib

    def png(width, height):
        def chunk(kind, value):
            return (
                struct.pack(">I", len(value))
                + kind
                + value
                + struct.pack(">I", zlib.crc32(kind + value))
            )

        data = b"\x89PNG\r\n\x1a\n" + chunk(
            b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
        )
        data += chunk(
            b"IDAT", zlib.compress((b"\0" + bytes(width * 4)) * height)
        ) + chunk(b"IEND", b"")
        return "data:image/png;base64," + base64.b64encode(data).decode()

    strip = png(576, 96)
    assert game.appearance({"pet": {"intro": strip}})["pet"]["intro"] == strip
    with pytest.raises(game.GameError):
        game.appearance({"pet": {"intro": png(128, 128)}})


def test_round_stays_open_at_thirty_seconds_and_expires_at_sixty():
    store, code, tokens = setup_game()
    with patch("game.time.time", return_value=100):
        game.start_game(store, code, tokens[0])
    with patch("game.time.time", return_value=103):
        first = game.get_game(store, code, tokens[0])
    assert first["deadline"] == 163
    with patch("game.time.time", return_value=133):
        assert game.get_game(store, code, tokens[0])["round"] == 1
    with patch("game.time.time", return_value=162.9):
        game.answer_game(store, code, tokens[0], 1, 2)
    with patch("game.time.time", return_value=163):
        state = game.get_game(store, code, tokens[1])
    assert state["round"] == 2
    assert state["deadline"] == 223
    assert state["history"][0]["answers"] == [True, None]
