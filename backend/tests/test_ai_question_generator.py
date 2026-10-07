"""Validation tests for batched assessment question generation."""

import json
import unittest

from app.services.ai_question_generator import QuestionGeneratorError, _parse_json, generate_question_batch


class FakeProvider:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def generate(self, messages: list[dict[str, str]]) -> str:
        return json.dumps(self.payload)


def question(prompt: str, topic: str = "Algebra") -> dict[str, object]:
    return {
        "topic": topic,
        "prompt": prompt,
        "options": ["one", "two", "three", "four"],
        "correct_option_index": 0,
        "explanation": "Because one is correct.",
        "difficulty": "medium",
        "question_type": "multiple_choice",
    }


class QuestionBatchTests(unittest.TestCase):
    def test_parses_json_inside_common_markdown_and_prose_wrappers(self) -> None:
        expected = {"questions": [question("Question one")]}
        encoded = json.dumps(expected)

        self.assertEqual(_parse_json(f"```json\n{encoded}\n```"), expected)
        self.assertEqual(_parse_json(f"Here is the result:\n{encoded}\nDone."), expected)

    def test_validates_and_returns_all_questions_with_topics(self) -> None:
        generated = generate_question_batch(
            subject="Mathematics",
            difficulty="medium",
            topics=["Algebra", "Trigonometry"],
            count=2,
            provider=FakeProvider({"questions": [question("Question one"), question("Question two", "Trigonometry")]}),
        )

        self.assertEqual(len(generated), 2)
        self.assertEqual({item.topic for item in generated}, {"Algebra", "Trigonometry"})
        self.assertTrue(all(len(item.options) == 4 for item in generated))

    def test_rejects_wrong_question_count_and_duplicate_options(self) -> None:
        with self.assertRaises(QuestionGeneratorError):
            generate_question_batch(
                subject="Mathematics",
                difficulty="medium",
                topics=["Algebra"],
                count=2,
                provider=FakeProvider({"questions": [question("Only one")]}),
            )

        invalid = question("Duplicate choices")
        invalid["options"] = ["same", "same", "three", "four"]
        with self.assertRaises(QuestionGeneratorError):
            generate_question_batch(
                subject="Mathematics",
                difficulty="medium",
                topics=["Algebra"],
                count=1,
                provider=FakeProvider({"questions": [invalid]}),
            )


if __name__ == "__main__":
    unittest.main()
