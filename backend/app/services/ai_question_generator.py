"""Validated AI-assisted question generation for the adaptive assessment bank."""

import json
from dataclasses import dataclass
from typing import Protocol

from app.services.ai_provider import AIProviderError, get_ai_provider


class QuestionGeneratorError(AIProviderError):
    """Raised when an AI response is not a valid assessment question."""


class QuestionProvider(Protocol):
    def generate(self, messages: list[dict[str, str]]) -> str:
        """Generate structured question content."""


@dataclass(frozen=True)
class GeneratedQuestion:
    prompt: str
    options: list[str]
    correct_option_index: int
    explanation: str
    difficulty: str
    question_type: str = "multiple_choice"
    topic: str | None = None


def _parse_json(response: str) -> dict[str, object]:
    decoder = json.JSONDecoder()
    for index, character in enumerate(response):
        if character != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(response, index)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise QuestionGeneratorError("AI question response was not valid JSON")


def generate_question(
    subject: str,
    difficulty: str,
    topic: str | None = None,
    provider: QuestionProvider | None = None,
) -> GeneratedQuestion:
    """Generate one validated NDA-style multiple-choice question."""
    provider = provider or get_ai_provider()
    context = f"Subject: {subject}\nDifficulty: {difficulty}"
    if topic:
        context += f"\nTopic: {topic}"
    response = provider.generate([
        {
            "role": "system",
            "content": (
                "You generate NDA-style educational practice questions. "
                "Use the requested subject and difficulty. Do not copy a past-paper question verbatim. "
                "Return only JSON with keys prompt, options, correct_option_index, explanation, difficulty, question_type. "
                "Use exactly four options, a zero-based correct_option_index, and question_type multiple_choice."
            ),
        },
        {"role": "user", "content": context},
    ])
    payload = _parse_json(response)
    return _validated_question(payload, difficulty)


def generate_question_batch(
    subject: str,
    difficulty: str,
    topics: list[str],
    count: int = 5,
    provider: QuestionProvider | None = None,
) -> list[GeneratedQuestion]:
    """Generate and validate a small diverse batch in one provider request."""
    if not topics:
        raise QuestionGeneratorError("At least one syllabus topic is required")
    if not 1 <= count <= 10:
        raise ValueError("Question batch size must be between 1 and 10")
    provider = provider or get_ai_provider()
    response = provider.generate([
        {
            "role": "system",
            "content": (
                "You generate original NDA-style educational practice questions. "
                "Use only the supplied syllabus topics and requested subject/difficulty. "
                "Do not copy past-paper questions verbatim. Return one valid JSON object only: "
                "no markdown fences, preamble, or text before or after it. Use double quotes "
                "for every property name and string. Return only JSON with one top-level "
                "key `questions`, containing exactly the requested number of objects. Each object "
                "must have topic, prompt, options, correct_option_index, explanation, difficulty, "
                "question_type. Use exactly four distinct options, zero-based correct_option_index, "
                "and question_type multiple_choice. Match all keys and types exactly; do not add "
                "extra properties or omit required fields."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Subject: {subject}\nDifficulty: {difficulty}\n"
                f"Allowed topics: {json.dumps(topics)}\nGenerate exactly {count} questions, "
                "covering different topics where possible."
            ),
        },
    ])
    payload = _parse_json(response)
    items = payload.get("questions")
    if not isinstance(items, list) or len(items) != count:
        raise QuestionGeneratorError(f"AI question response must contain exactly {count} questions")
    allowed_topics = {topic.casefold() for topic in topics}
    generated: list[GeneratedQuestion] = []
    seen_prompts: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise QuestionGeneratorError("Each generated question must be a JSON object")
        question = _validated_question(item, difficulty)
        topic = item.get("topic")
        if not isinstance(topic, str) or topic.casefold() not in allowed_topics:
            raise QuestionGeneratorError("Generated question topic is not in the supplied syllabus")
        normalized_prompt = question.prompt.casefold()
        if normalized_prompt in seen_prompts:
            raise QuestionGeneratorError("Generated question batch contains duplicate prompts")
        seen_prompts.add(normalized_prompt)
        generated.append(GeneratedQuestion(
            prompt=question.prompt,
            options=question.options,
            correct_option_index=question.correct_option_index,
            explanation=question.explanation,
            difficulty=question.difficulty,
            topic=topic,
        ))
    return generated


def _validated_question(payload: dict[str, object], difficulty: str) -> GeneratedQuestion:
    prompt = payload.get("prompt")
    options = payload.get("options")
    correct_index = payload.get("correct_option_index")
    explanation = payload.get("explanation")
    response_difficulty = payload.get("difficulty")
    if not isinstance(prompt, str) or not prompt.strip():
        raise QuestionGeneratorError("Generated question has no prompt")
    if (
        not isinstance(options, list)
        or len(options) != 4
        or not all(isinstance(option, str) and option.strip() for option in options)
        or len({option.strip().casefold() for option in options}) != 4
    ):
        raise QuestionGeneratorError("Generated question must contain exactly four text options")
    if type(correct_index) is not int or not 0 <= correct_index < len(options):
        raise QuestionGeneratorError("Generated question has an invalid correct option")
    if not isinstance(explanation, str) or not explanation.strip():
        raise QuestionGeneratorError("Generated question has no explanation")
    if response_difficulty != difficulty:
        raise QuestionGeneratorError("Generated question difficulty did not match the requested difficulty")
    if payload.get("question_type") != "multiple_choice":
        raise QuestionGeneratorError("Generated question must be multiple choice")
    return GeneratedQuestion(
        prompt=prompt.strip(),
        options=[option.strip() for option in options],
        correct_option_index=correct_index,
        explanation=explanation.strip(),
        difficulty=difficulty,
    )
