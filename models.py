from typing import Literal

from pydantic import BaseModel, model_validator

Category = Literal[
    "geography", "art", "maths", "biology", "history", "music", "science"
]
OptionId = Literal["A", "B", "C", "D"]


class Option(BaseModel):
    id: OptionId
    text: str


class GeneratedQuestion(BaseModel):
    category: Category
    difficulty: Literal["standard", "hard"]
    question: str
    options: list[Option]
    correct_answer: OptionId

    @model_validator(mode="after")
    def validate_question(self):
        if not self.question.strip():
            raise ValueError("Question must not be empty")
        if len(self.options) != 4 or {o.id for o in self.options} != set("ABCD"):
            raise ValueError(
                "Exactly one option for each ID A, B, C, and D is required"
            )
        texts = [o.text.strip().casefold() for o in self.options]
        if not all(texts) or len(set(texts)) != 4:
            raise ValueError("Option texts must be non-empty and distinct")
        return self


class QuestionSet(BaseModel):
    questions: list[GeneratedQuestion]


class PetDecision(BaseModel):
    answer: OptionId
    needs_help: bool
    message: str
