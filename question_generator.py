import os
from collections import Counter

from openai import APIError, OpenAI
from pydantic import ValidationError

from models import QuestionSet


class GenerationError(Exception):
    pass


class ConfigurationError(GenerationError):
    pass


def generate_questions(first_category, second_category, random_category):
    if not os.getenv("OPENAI_API_KEY"):
        raise ConfigurationError("OPENAI_API_KEY is not configured on the server.")
    try:
        client = OpenAI(timeout=30.0, max_retries=1)
        response = client.responses.parse(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            input=[
                {
                    "role": "system",
                    "content": (
                        "Create five distinct, clear multiple-choice learning questions for children aged 8 to 12. Use familiar examples and simple vocabulary. Avoid adult content and trick questions. "
                        "Each must have exactly four distinct options labelled A, B, C and D, "
                        "one unambiguously correct answer and three plausible incorrect answers. "
                        "Use concise plain text and ensure every answer is factually correct. "
                        "Return each question with its requested category."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Create two questions in {first_category}, two in {second_category}, and one in {random_category}.",
                },
            ],
            text_format=QuestionSet,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise GenerationError("The model did not return complete questions.")
        expected = Counter({first_category: 2, second_category: 2, random_category: 1})
        if Counter(q.category for q in parsed.questions) != expected:
            raise GenerationError(
                "The model returned an invalid category distribution."
            )
        if len({q.question.strip().casefold() for q in parsed.questions}) != 5:
            raise GenerationError("The model returned duplicate questions.")
        questions = []
        for question in parsed.questions:
            options = sorted(question.options, key=lambda option: option.id)
            questions.append(
                {
                    "category": question.category,
                    "prompt": question.question,
                    "options": [option.text for option in options],
                    "answer": ord(question.correct_answer) - ord("A"),
                }
            )
        return questions
    except (APIError, ValidationError) as exc:
        raise GenerationError("Question generation failed. Please try again.") from exc
