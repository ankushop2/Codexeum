from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app as api
import question_generator
from models import GeneratedQuestion, Question


@pytest.fixture
def sample():
    return {
        "question": "What is 1 + 1?",
        "options": [
            {"id": "A", "text": "1"},
            {"id": "B", "text": "2"},
            {"id": "C", "text": "3"},
            {"id": "D", "text": "4"},
        ],
        "correct_answer": "B",
    }


def test_api_returns_question(monkeypatch, sample):
    monkeypatch.setattr(
        api, "generate_question", lambda category: Question(category=category, **sample)
    )
    client = TestClient(api.app)
    assert client.get("/api/health").json()["status"] == "ok"
    assert len(client.get("/api/skills").json()["skills"]) == 7
    response = client.post("/api/questions", json={"category": "python"})
    assert response.status_code == 200
    assert response.json() == {"category": "python", **sample}
    assert (
        client.post("/api/questions", json={"category": "unknown"}).status_code == 422
    )


def test_invalid_generated_questions(sample):
    sample["options"][0]["text"] = " 2 "
    with pytest.raises(ValidationError):
        GeneratedQuestion(**sample)
    sample["options"][0]["text"] = "1"
    sample["options"].pop()
    with pytest.raises(ValidationError):
        GeneratedQuestion(**sample)


def test_generator_calls_openai(monkeypatch, sample):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    client = Mock()
    client.responses.parse.return_value.output_parsed = GeneratedQuestion(**sample)
    monkeypatch.setattr(question_generator, "OpenAI", lambda **kwargs: client)
    assert question_generator.generate_question("logic").category == "logic"
    assert client.responses.parse.call_args.kwargs["text_format"] is GeneratedQuestion


def test_generation_errors(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(api.app)
    assert client.post("/api/questions", json={"category": "python"}).status_code == 503

    def fail(category):
        raise question_generator.GenerationError("Generation failed")

    monkeypatch.setattr(api, "generate_question", fail)
    response = client.post("/api/questions", json={"category": "python"})
    assert response.status_code == 502
    assert response.json()["detail"] == "Generation failed"
