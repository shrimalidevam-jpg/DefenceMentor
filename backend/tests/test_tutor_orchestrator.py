import unittest

from app.services.tutor_orchestrator import orchestrate_tutor_turn


class TutorOrchestratorTests(unittest.TestCase):
    def test_new_topic_starts_with_attempt_check(self) -> None:
        turn = orchestrate_tutor_turn("Explain probability", [], "started")
        self.assertEqual(turn.next_state, "awaiting_attempt_status")
        self.assertIn("ask whether they have tried", turn.guidance)

    def test_yes_response_invites_student_explanation(self) -> None:
        turn = orchestrate_tutor_turn(
            "Yes, I read about it",
            [{"role": "user", "content": "Explain probability"}],
            "awaiting_attempt_status",
        )
        self.assertEqual(turn.next_state, "awaiting_student_explanation")
        self.assertIn("what they understood", turn.guidance)
        self.assertIn("what is still unclear", turn.guidance)

    def test_no_response_asks_what_is_unclear(self) -> None:
        turn = orchestrate_tutor_turn(
            "No, I didn't understand it",
            [{"role": "user", "content": "Explain probability"}],
            "awaiting_attempt_status",
        )
        self.assertEqual(turn.next_state, "awaiting_confusion_detail")
        self.assertIn("which exact part", turn.guidance)

    def test_explanation_is_evaluated_and_corrected(self) -> None:
        turn = orchestrate_tutor_turn(
            "Probability is the number of outcomes.",
            [],
            "awaiting_student_explanation",
        )
        self.assertEqual(turn.next_state, "awaiting_confusion_detail")
        self.assertIn("gently correct", turn.guidance)
        self.assertIn("Do not simply agree", turn.guidance)

    def test_confusion_detail_is_explained_then_student_retries(self) -> None:
        turn = orchestrate_tutor_turn(
            "I don't understand what sample space means",
            [],
            "awaiting_confusion_detail",
        )
        self.assertEqual(turn.next_state, "awaiting_student_explanation")
        self.assertIn("exact part", turn.guidance)
        self.assertIn("invite them to explain", turn.guidance)

    def test_non_study_messages_do_not_start_teach_back(self) -> None:
        turn = orchestrate_tutor_turn("Thanks", [], "started")
        self.assertEqual(turn.next_state, "ai_response")
        self.assertIn("non-study message", turn.guidance)

    def test_math_topic_prompts_attempt_before_teaching(self) -> None:
        turn = orchestrate_tutor_turn("Explain fractions", [], None)
        self.assertEqual(turn.next_state, "awaiting_attempt_status")
        self.assertIn("Do not solve it or reveal the answer yet", turn.guidance)
        self.assertIn("explain it in their own words", turn.guidance)

    def test_hindi_math_question_uses_hindi_guidance_and_english_reminder(self) -> None:
        turn = orchestrate_tutor_turn("गणित में भिन्न क्या हैं?", [], None)
        self.assertEqual(turn.next_state, "awaiting_attempt_status")
        self.assertIn("Reply in natural, clear Hindi", turn.guidance)
        self.assertIn("keep practising English", turn.guidance)

    def test_explicit_hindi_request_overrides_english_message(self) -> None:
        message = "Explain probability in Hindi."
        turn = orchestrate_tutor_turn(message, [{"role": "user", "content": message}], None)

        self.assertEqual(turn.next_state, "ai_response")
        self.assertIn("The student requested Hindi", turn.guidance)
        self.assertIn("even if the request or conversation is written in English", turn.guidance)
        self.assertIn("Give the explanation now", turn.guidance)

    def test_explicit_hindi_request_persists_through_english_follow_up(self) -> None:
        turn = orchestrate_tutor_turn(
            "Yes, I tried",
            [
                {"role": "user", "content": "Explain probability in Hindi."},
                {"role": "assistant", "content": "Have you tried studying it?"},
                {"role": "user", "content": "Yes, I tried"},
            ],
            "awaiting_attempt_status",
        )

        self.assertEqual(turn.next_state, "awaiting_student_explanation")
        self.assertIn("Reply in natural, clear Hindi", turn.guidance)

    def test_hindi_attempt_answer_keeps_the_teach_back_flow(self) -> None:
        turn = orchestrate_tutor_turn("हाँ, मैंने कोशिश की", [], "awaiting_attempt_status")
        self.assertEqual(turn.next_state, "awaiting_student_explanation")
        self.assertIn("explain in their own words", turn.guidance)

    def test_unrelated_question_gets_focus_redirect_without_ai_provider(self) -> None:
        turn = orchestrate_tutor_turn("Tell me a cricket joke", [], None)
        self.assertEqual(turn.next_state, "ai_response")
        self.assertEqual(
            turn.fixed_response,
            "**Do not lose your focus.** Let’s get back to NDA preparation—which subject would you like to work on?",
        )


if __name__ == "__main__":
    unittest.main()
