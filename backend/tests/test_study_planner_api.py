"""Tests for the personalized daily study planner."""

import unittest
from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.base import Base
from app.models.curriculum import Chapter, Concept, Exam, Subject, Topic
from app.models.enums import UserRole
from app.models.users import StudentProfile, User


class StudyPlannerApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(cls.engine)
        cls.session_factory = sessionmaker(bind=cls.engine, autoflush=False)

        def override_database():
            database = cls.session_factory()
            try:
                yield database
            finally:
                database.close()

        app.dependency_overrides[get_db] = override_database
        cls.client = TestClient(app)
        database = cls.session_factory()
        cls.user_id = uuid4()
        exam = Exam(id=uuid4(), name="NDA Planner Exam", code="NDA")
        subject = Subject(id=uuid4(), exam_id=exam.id, name="Mathematics", code="MATH")
        chapter = Chapter(id=uuid4(), subject_id=subject.id, name="Arithmetic")
        topic = Topic(id=uuid4(), chapter_id=chapter.id, name="Fractions")
        concepts = [Concept(id=uuid4(), topic_id=topic.id, name=f"Concept {index}") for index in range(4)]
        database.add_all([
            User(id=cls.user_id, email="planner@example.com", full_name="Planner Student", password_hash=hash_password("SecurePass9"), role=UserRole.STUDENT),
            StudentProfile(user_id=cls.user_id, exam_target="NDA"),
            exam, subject, chapter, topic, *concepts,
        ])
        database.commit()
        cls.headers = {"Authorization": f"Bearer {create_access_token(str(cls.user_id), 'student')}"}
        database.close()

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        cls.engine.dispose()

    def test_daily_plan_is_generated_and_completion_persists(self) -> None:
        response = self.client.get("/api/study-planner/today", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        plan = response.json()
        self.assertEqual(len(plan["tasks"]), 3)
        self.assertEqual(plan["exam_target"], "NDA")
        self.assertEqual(plan["total_minutes"], sum(task["estimated_minutes"] for task in plan["tasks"]))

        task_id = plan["tasks"][0]["id"]
        updated = self.client.patch(f"/api/study-planner/tasks/{task_id}", headers=self.headers, json={"is_completed": True})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["completed_count"], 1)
        self.assertTrue(next(task for task in updated.json()["tasks"] if task["id"] == task_id)["is_completed"])

        reloaded = self.client.get("/api/study-planner/today", headers=self.headers)
        self.assertEqual(reloaded.status_code, 200)
        self.assertEqual(reloaded.json()["completed_count"], 1)

    def test_user_cannot_update_another_users_task(self) -> None:
        plan = self.client.get("/api/study-planner/today", headers=self.headers).json()
        other_user_id = uuid4()
        other_headers = {"Authorization": f"Bearer {create_access_token(str(other_user_id), 'student')}"}
        response = self.client.patch(f"/api/study-planner/tasks/{plan['tasks'][0]['id']}", headers=other_headers, json={"is_completed": True})
        self.assertEqual(response.status_code, 401)

    def test_tomorrow_plan_carries_unfinished_tasks_and_cannot_be_completed_early(self) -> None:
        today = self.client.get("/api/study-planner/today", headers=self.headers).json()
        unfinished = next((task for task in today["tasks"] if not task["is_completed"]), None)
        tomorrow = self.client.get("/api/study-planner/tomorrow", headers=self.headers)
        self.assertEqual(tomorrow.status_code, 200)
        body = tomorrow.json()
        self.assertEqual(len(body["tasks"]), 3)
        self.assertEqual(body["plan_date"], (date.today() + timedelta(days=1)).isoformat())
        if unfinished:
            self.assertEqual(body["tasks"][0]["concept_id"], unfinished["concept_id"])

        response = self.client.patch(
            f"/api/study-planner/tasks/{body['tasks'][0]['id']}",
            headers=self.headers,
            json={"is_completed": True},
        )
        self.assertEqual(response.status_code, 409)

        refreshed = self.client.post("/api/study-planner/tomorrow/regenerate", headers=self.headers)
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(refreshed.json()["plan_date"], body["plan_date"])


if __name__ == "__main__":
    unittest.main()
