import os
from collections import Counter
from typing import Any

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
                        "Create five distinct multiple-choice questions at UK A-level difficulty (ages 16 to 18). "
                        "Every question, including the random-category question, must require advanced subject "
                        "knowledge, application of concepts, or compact multi-step reasoning, rather than basic recall or general trivia. "
                        "Target subject-specific A-level depth: mathematical problem-solving, scientific mechanisms "
                        "and interpretation of evidence, geographic processes, historical causation and source interpretation, "
                        "or art and music theory and contextual analysis as appropriate. "
                        "Keep stems concise enough for a 30-second quiz; supply any necessary data, assumptions and units. "
                        "Each must have exactly four distinct options labelled A, B, C and D, one unambiguously "
                        "correct answer, and three plausible distractors based on common misconceptions or reasoning errors. "
                        "Check calculations and factual accuracy before returning the questions. Avoid subjective, ambiguous "
                        "or trick questions and do not include the solution in the stem. "
                        "Return each question with its requested category and difficulty set to hard. "
                        "Make the questions challenging enough that a pet's 50/50 elimination hint is useful."
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
        expected_difficulties = Counter(
            {
                (first_category, "hard"): 2,
                (second_category, "hard"): 2,
                (random_category, "hard"): 1,
            }
        )
        if (
            Counter((q.category, q.difficulty) for q in parsed.questions)
            != expected_difficulties
        ):
            raise GenerationError(
                "The model returned an invalid difficulty distribution."
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
                    "difficulty": question.difficulty,
                    "options": [option.text for option in options],
                    "answer": ord(question.correct_answer) - ord("A"),
                }
            )
        return questions
    except (APIError, ValidationError) as exc:
        raise GenerationError("Question generation failed. Please try again.") from exc


def choose_eliminations(question, guidance=""):
    from itertools import combinations

    if not os.getenv("OPENAI_API_KEY"):
        raise ConfigurationError("OPENAI_API_KEY is not configured on the server.")
    wrong = [i for i in range(len(question["options"])) if i != question["answer"]]
    pairs = {f"{a},{b}": [a, b] for a, b in combinations(wrong, 2)}
    options = "\n".join(
        f"{chr(65 + i)}. {text}" for i, text in enumerate(question["options"])
    )
    try:
        decision = OpenAI(timeout=7.0, max_retries=0).post(
            "/decisions",
            cast_to=dict[str, Any],
            body={
                "model": os.getenv("PET_MODEL", "gpt-6-luna"),
                "input": f"Question: {question['prompt']}\n{options}\nTrainer guidance: {guidance}",
                "questions": [
                    {
                        "type": "choice",
                        "name": "eliminate",
                        "instructions": "Help an A-level learner reason about this quiz by removing two incorrect options. Choose the most useful pair of distractors to eliminate. Only choose from the supplied safe pairs.",
                        "choices": [
                            {
                                "value": key,
                                "description": f"Eliminate {chr(65 + value[0])} and {chr(65 + value[1])}",
                            }
                            for key, value in pairs.items()
                        ],
                    }
                ],
            },
        )
        answers = decision.get("answers", [])
        if (
            len(answers) != 1
            or answers[0].get("type") != "choice"
            or answers[0].get("choice") not in pairs
        ):
            raise GenerationError("Your pet couldn't narrow the choices. Try again.")
        return pairs[answers[0]["choice"]]
    except APIError as exc:
        raise GenerationError("Your pet couldn't respond. Try again.") from exc
