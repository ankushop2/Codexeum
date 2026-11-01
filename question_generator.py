import os

from openai import APIError, OpenAI
from pydantic import ValidationError

from models import Category, GeneratedQuestion, Question


class GenerationError(Exception):
    pass


class ConfigurationError(GenerationError):
    pass


def generate_question(category: Category) -> Question:
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
                        "Create one clear, moderately difficult multiple-choice question. "
                        "Include exactly four distinct options with IDs A, B, C, and D, "
                        "one unambiguously correct answer, and three plausible incorrect answers. "
                        "Use concise plain text; short code snippets are welcome when appropriate."
                    ),
                },
                {"role": "user", "content": f"Category: {category}"},
            ],
            text_format=GeneratedQuestion,
        )
        if response.output_parsed is None:
            raise GenerationError("The model did not return a complete question.")
        return Question(category=category, **response.output_parsed.model_dump())
    except (APIError, ValidationError) as exc:
        raise GenerationError("Question generation failed. Please try again.") from exc
