from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app as api
import game
import question_generator
from models import GeneratedQuestion, QuestionSet
from test_game import MemoryStore


@pytest.fixture
def sample():
    return {
        "category": "maths",
        "difficulty": "hard",
        "question": "What is 1 + 1?",
        "options": [
            {"id": "A", "text": "1"},
            {"id": "B", "text": "2"},
            {"id": "C", "text": "3"},
            {"id": "D", "text": "4"},
        ],
        "correct_answer": "B",
    }


def test_invalid_generated_questions(sample):
    sample["options"][0]["text"] = " 2 "
    with pytest.raises(ValidationError):
        GeneratedQuestion(**sample)
    sample["options"][0]["text"] = "1"
    sample["options"].pop()
    with pytest.raises(ValidationError):
        GeneratedQuestion(**sample)


def test_generator_requests_five_questions(monkeypatch, sample):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    client = Mock()
    categories = ["maths", "maths", "geography", "geography", "art"]
    questions = [
        GeneratedQuestion(
            **{
                **sample,
                "category": category,
                "question": f"Question {i}",
                "difficulty": "hard",
            }
        )
        for i, category in enumerate(categories)
    ]
    client.responses.parse.return_value.output_parsed = QuestionSet(questions=questions)
    monkeypatch.setattr(question_generator, "OpenAI", lambda **kwargs: client)
    result = question_generator.generate_questions("maths", "geography", "art")
    assert [q["category"] for q in result] == categories
    assert all(q["answer"] == 1 for q in result if q["category"] != "geography")
    continents = {
        "Kenya": "Africa",
        "Brazil": "South America",
        "France": "Europe",
        "Japan": "Asia",
        "Canada": "North America",
        "Australia": "Oceania",
    }
    for question in result:
        if question["category"] == "geography":
            assert question["kind"] == "map"
            country = (
                question["prompt"]
                .removeprefix("Tap the continent where ")
                .removesuffix(" is located.")
            )
            assert question["options"][question["answer"]] == continents[country]
    assert all(q["difficulty"] == "hard" for q in result)
    prompt = client.responses.parse.call_args.kwargs["input"][0]["content"]
    assert "UK A-level" in prompt
    assert "random-category question" in prompt
    assert client.responses.parse.call_args.kwargs["text_format"] is QuestionSet
    with pytest.raises(question_generator.GenerationError):
        question_generator.generate_questions("maths", "geography", "biology")
    questions[1].difficulty = "standard"
    with pytest.raises(question_generator.GenerationError):
        question_generator.generate_questions("maths", "geography", "art")


def test_join_generation_failure_leaves_room_waiting(monkeypatch):
    store = MemoryStore()
    monkeypatch.setattr(api, "store", store)

    def fail(*args):
        raise question_generator.GenerationError("Generation failed")

    monkeypatch.setattr(game, "generate_questions", fail)
    client = TestClient(api.app)
    first = client.post("/api/games", json={"category": "maths"}).json()
    second = client.post(
        f"/api/games/{first['code']}/join", json={"category": "geography"}
    ).json()
    client.post(
        f"/api/games/{first['code']}/ready",
        headers={"Authorization": "Bearer " + first["token"]},
    )
    result = client.post(
        f"/api/games/{first['code']}/ready",
        headers={"Authorization": "Bearer " + second["token"]},
    )
    assert result.status_code == 502
    state = client.get(
        f"/api/games/{first['code']}",
        headers={"Authorization": "Bearer " + first["token"]},
    )
    assert state.json()["phase"] == "waiting"
    assert len(state.json()["players"]) == 2
    assert client.post("/api/questions", json={"category": "maths"}).status_code in (
        404,
        405,
    )
