import os
from collections import Counter
from typing import Any

from openai import APIError, OpenAI
from pydantic import ValidationError

from interactive_questions import interactive_questions
from models import QuestionSet


class GenerationError(Exception):
    pass


class ConfigurationError(GenerationError):
    pass


DIFFICULTY_PROMPTS = {
    "easy": "Use beginner-friendly knowledge, clear vocabulary and simple recall or one-step reasoning. Avoid obscure trivia.",
    "med": "Require solid subject knowledge and application of concepts, with short calculations or a few reasoning steps. Avoid trivial recall and specialist-only knowledge.",
    "hard": "Require advanced subject knowledge, challenging application or compact multi-step reasoning, with plausible distractors based on common misconceptions. Avoid ambiguous or trick questions.",
}


def generate_questions(
    first_category, second_category, random_category, difficulty="med"
):
    if difficulty not in DIFFICULTY_PROMPTS:
        raise GenerationError("Invalid question difficulty.")
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
                        "Create five distinct multiple-choice quiz questions at the requested difficulty. "
                        "Apply that difficulty to every question, including the random category. "
                        "For Code questions, cover Python, JavaScript or debugging and clearly state the language. "
                        "Keep stems concise enough for a 60-second quiz; supply necessary data, assumptions and units. "
                        "Each question must have four distinct options labelled A, B, C and D, one unambiguously "
                        "correct answer and three plausible distractors. Check calculations and factual accuracy. "
                        "Return the requested category and difficulty label on every question. "
                        + DIFFICULTY_PROMPTS[difficulty]
                    ),
                },
                {
                    "role": "user",
                    "content": f"Difficulty: {difficulty}. Create two questions in {first_category}, two in {second_category}, and one in {random_category}.",
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
                (first_category, difficulty): 2,
                (second_category, difficulty): 2,
                (random_category, difficulty): 1,
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
        return interactive_questions(questions) if difficulty == "easy" else questions
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
                        "instructions": "Help the learner reason about this quiz by removing two incorrect options. Choose the most useful pair of distractors to eliminate. Only choose from the supplied safe pairs.",
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
