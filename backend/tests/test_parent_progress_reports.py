"""Parent report scheduling and WhatsApp payload tests."""

from datetime import date
import unittest
from unittest.mock import Mock, patch

from app.core.config import settings
from app.services.parent_progress_reports import _report_window, _send_whatsapp_template


class ParentProgressReportTests(unittest.TestCase):
    def test_weekly_window_runs_monday_through_sunday(self) -> None:
        self.assertEqual(
            _report_window("weekly", date(2026, 10, 7)),
            (date(2026, 10, 5), date(2026, 10, 11)),
        )

    def test_monthly_window_handles_year_boundary(self) -> None:
        self.assertEqual(
            _report_window("monthly", date(2026, 12, 31)),
            (date(2026, 12, 1), date(2026, 12, 31)),
        )

    def test_whatsapp_template_uses_configured_template_and_guardian_number(self) -> None:
        response = Mock()
        response.json.return_value = {"messages": [{"id": "wamid.test"}]}
        with patch.object(settings, "WHATSAPP_ACCESS_TOKEN", "test-token"), \
                patch.object(settings, "WHATSAPP_PHONE_NUMBER_ID", "phone-id"), \
                patch.object(settings, "WHATSAPP_TEMPLATE_NAME", "nda_progress_report"), \
                patch("app.services.parent_progress_reports.httpx.post", return_value=response) as post:
            message_id = _send_whatsapp_template("+919876543210", "Student", "weekly", "Good progress")

        self.assertEqual(message_id, "wamid.test")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["to"], "919876543210")
        self.assertEqual(payload["template"]["name"], "nda_progress_report")
        self.assertEqual(
            [item["text"] for item in payload["template"]["components"][0]["parameters"]],
            ["Student", "Weekly", "Good progress"],
        )


if __name__ == "__main__":
    unittest.main()
