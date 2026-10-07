"""Schema-level regression tests that do not require PostgreSQL."""
import importlib.util
from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session
from app.models import *  # noqa: F403
from app.models.base import Base
from app.models.curriculum import Chapter, Concept, Exam, Subject, Topic

class DatabaseSchemaTests(unittest.TestCase):
    def test_initial_schema_creates_all_expected_tables(self) -> None:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        table_names = set(inspect(engine).get_table_names())
        expected_tables = {
            "users", "student_profiles", "exams", "subjects", "chapters", "topics", "concepts",
            "prerequisites", "questions", "question_options", "question_answers", "question_attempts",
            "student_mastery", "learning_sessions", "learning_progress", "chat_sessions", "chat_messages",
            "assessments", "assessment_attempts", "assessment_questions", "sources", "content_documents",
            "content_chunks", "notifications", "admin_users",
        }
        self.assertTrue(expected_tables.issubset(table_names))
        self.assertIn("attachments", {column["name"] for column in inspect(engine).get_columns("chat_messages")})
        self.assertTrue({"daily_ssb_guidance", "ssb_guidance_messages"}.issubset(table_names))

    def test_ssb_guidance_migration_creates_and_drops_its_tables(self) -> None:
        engine = create_engine("sqlite://")
        Base.metadata.tables["users"].create(engine)
        migration_path = Path(__file__).parents[1] / "alembic" / "versions" / "20261007_0030_ssb_guidance.py"
        spec = importlib.util.spec_from_file_location("ssb_guidance_migration", migration_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        self.assertTrue({"daily_ssb_guidance", "ssb_guidance_messages"}.issubset(inspect(engine).get_table_names()))

        with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        self.assertFalse({"daily_ssb_guidance", "ssb_guidance_messages"} & set(inspect(engine).get_table_names()))
        engine.dispose()

    def test_prerequisite_graph_prevents_duplicate_edges(self) -> None:
        prerequisite = Base.metadata.tables["prerequisites"]
        constraints = [item for item in prerequisite.constraints if item.__class__.__name__ == "UniqueConstraint"]
        self.assertTrue(any(
            {column.name for column in item.columns} == {"concept_id", "prerequisite_concept_id"}
            for item in constraints
        ))

    def test_nda_math_syllabus_migration_adds_chapters_idempotently(self) -> None:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            exam = Exam(name="NDA syllabus test", code="NDA-SYLLABUS")
            connection_session = Session(bind=connection, join_transaction_mode="create_savepoint")
            connection_session.add(exam)
            connection_session.flush()
            subject = Subject(exam_id=exam.id, name="Mathematics", code="MATH", display_order=1)
            connection_session.add(subject)
            connection_session.flush()
            algebra = Chapter(subject_id=subject.id, name="Algebra", display_order=1)
            arithmetic = Chapter(subject_id=subject.id, name="Arithmetic", display_order=2)
            connection_session.add_all([algebra, arithmetic])
            connection_session.flush()
            old_probability = Topic(chapter_id=arithmetic.id, name="Probability", display_order=3)
            connection_session.add(old_probability)
            connection_session.flush()
            old_probability_id = old_probability.id
            connection_session.commit()

            migration_path = Path(__file__).parents[1] / "alembic" / "versions" / "20261007_0026_nda_maths_syllabus.py"
            spec = importlib.util.spec_from_file_location("nda_maths_syllabus_migration", migration_path)
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.loader)
            migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration)

            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
                migration.upgrade()

            chapters = list(connection_session.scalars(select(Chapter).where(Chapter.subject_id == subject.id).order_by(Chapter.display_order)))
            chapter_names = [chapter.name for chapter in chapters]
            self.assertEqual(chapter_names[:8], [
                "Algebra",
                "Matrices and Determinants",
                "Trigonometry",
                "Analytical Geometry of Two and Three Dimensions",
                "Differential Calculus",
                "Integral Calculus and Differential Equations",
                "Vector Algebra",
                "Statistics and Probability",
            ])
            self.assertEqual(chapter_names[-1], "Arithmetic")
            statistics_chapter = next(chapter for chapter in chapters if chapter.name == "Statistics and Probability")
            probability = connection_session.scalar(select(Topic).where(Topic.name == "Probability", Topic.chapter_id == statistics_chapter.id))
            self.assertEqual(probability.id, old_probability_id)
            syllabus_concept = connection_session.scalar(select(Concept).where(Concept.name == "De Morgan laws"))
            self.assertIsNotNone(syllabus_concept)
            self.assertEqual(
                connection_session.scalar(select(func.count()).select_from(Concept).where(Concept.name == "De Morgan laws")),
                1,
            )
            connection_session.close()

        engine.dispose()

    def test_nda_english_syllabus_migration_adds_topics_idempotently(self) -> None:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            session = Session(bind=connection, join_transaction_mode="create_savepoint")
            exam = Exam(name="NDA English syllabus test", code="NDA-ENGLISH-SYLLABUS")
            session.add(exam)
            session.flush()
            gat = Subject(exam_id=exam.id, name="General Ability Test", code="GAT", display_order=2)
            session.add(gat)
            session.flush()
            foundations = Chapter(
                subject_id=gat.id,
                name="English and General Knowledge Foundations",
                display_order=1,
            )
            session.add(foundations)
            session.flush()
            starter = Topic(
                chapter_id=foundations.id,
                name="English",
                description="Starter English topic",
                display_order=1,
            )
            session.add(starter)
            session.flush()
            starter_concept = Concept(
                topic_id=starter.id,
                name="Reading comprehension, grammar and vocabulary",
                display_order=1,
            )
            session.add(starter_concept)
            session.commit()
            starter_id = starter.id

            migration_path = Path(__file__).parents[1] / "alembic" / "versions" / "20261007_0027_nda_english_syllabus.py"
            spec = importlib.util.spec_from_file_location("nda_english_syllabus_migration", migration_path)
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.loader)
            migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration)

            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
                migration.upgrade()

            session.expire_all()
            english_chapter = session.scalar(
                select(Chapter).where(Chapter.subject_id == gat.id, Chapter.name == "English")
            )
            topics = list(
                session.scalars(
                    select(Topic)
                    .where(Topic.chapter_id == english_chapter.id)
                    .order_by(Topic.display_order)
                )
            )
            self.assertEqual(
                [topic.name for topic in topics],
                [
                    "English Foundations",
                    "Spotting Errors",
                    "Comprehension",
                    "Selecting Words",
                    "Synonyms",
                    "Antonyms",
                    "Sentence Improvements",
                    "Ordering of Words in a Sentence",
                ],
            )
            self.assertEqual(topics[0].id, starter_id)
            self.assertEqual(
                session.scalar(
                    select(Concept.name).where(Concept.topic_id == starter_id)
                ),
                "Reading comprehension, grammar and vocabulary",
            )
            self.assertEqual(
                session.scalar(
                    select(func.count()).select_from(Topic).where(Topic.name == "Spotting Errors")
                ),
                1,
            )
            self.assertEqual(
                session.scalar(
                    select(func.count()).select_from(Concept).where(Concept.name == "Spotting Errors")
                ),
                1,
            )
            with Operations.context(MigrationContext.configure(connection)):
                migration.downgrade()
            session.expire_all()
            self.assertIsNone(
                session.scalar(
                    select(Chapter).where(Chapter.subject_id == gat.id, Chapter.name == "English")
                )
            )
            restored_starter = session.get(Topic, starter_id)
            self.assertEqual(restored_starter.name, "English")
            self.assertEqual(restored_starter.chapter_id, foundations.id)
            session.close()

        engine.dispose()

    def test_nda_gat_physics_chemistry_migration_is_idempotent_and_preserves_existing_content(self) -> None:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            session = Session(bind=connection, join_transaction_mode="create_savepoint")
            exam = Exam(name="NDA science syllabus test", code="NDA-SCIENCE-SYLLABUS")
            session.add(exam)
            session.flush()
            gat = Subject(exam_id=exam.id, name="General Ability Test", code="GAT", display_order=2)
            session.add(gat)
            session.flush()
            physics = Chapter(subject_id=gat.id, name="Physics", display_order=2)
            session.add(physics)
            session.flush()
            existing_topic = Topic(chapter_id=physics.id, name="Teacher-added topic", display_order=20)
            session.add(existing_topic)
            session.flush()
            existing_concept = Concept(topic_id=existing_topic.id, name="Teacher-added concept", display_order=1)
            session.add(existing_concept)
            session.commit()
            physics_id = physics.id

            migration_path = Path(__file__).parents[1] / "alembic" / "versions" / "20261007_0028_nda_gat_physics_chemistry.py"
            spec = importlib.util.spec_from_file_location("nda_gat_physics_chemistry_migration", migration_path)
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.loader)
            migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration)

            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
                migration.upgrade()

            session.expire_all()
            physics_topics = list(
                session.scalars(
                    select(Topic).where(Topic.chapter_id == physics_id).order_by(Topic.display_order)
                )
            )
            self.assertEqual(len(physics_topics), 9)
            self.assertEqual(physics_topics[-1].name, "Teacher-added topic")
            self.assertEqual(
                session.scalar(select(func.count()).select_from(Concept)),
                47,
            )

            with Operations.context(MigrationContext.configure(connection)):
                migration.downgrade()
            session.expire_all()
            self.assertEqual(session.get(Chapter, physics_id).name, "Physics")
            self.assertEqual(session.get(Topic, existing_topic.id).name, "Teacher-added topic")
            self.assertEqual(session.get(Concept, existing_concept.id).name, "Teacher-added concept")
            self.assertEqual(
                session.scalar(select(func.count()).select_from(Topic)),
                1,
            )
            session.close()

        engine.dispose()

    def test_nda_gat_general_knowledge_migration_is_idempotent_and_reversible(self) -> None:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            session = Session(bind=connection, join_transaction_mode="create_savepoint")
            exam = Exam(name="NDA general knowledge syllabus test", code="NDA-GK-SYLLABUS")
            session.add(exam)
            session.flush()
            gat = Subject(exam_id=exam.id, name="General Ability Test", code="GAT", display_order=2)
            session.add(gat)
            session.flush()
            foundation_chapter = Chapter(
                subject_id=gat.id,
                name="English and General Knowledge Foundations",
                display_order=1,
            )
            session.add(foundation_chapter)
            session.flush()
            foundation_data = (
                ("General Science", "Biology and basic science"),
                ("History", "Indian history and culture"),
                ("Geography", "India and world geography"),
                ("Current Events", "Current affairs and defence awareness"),
            )
            foundation_ids = {}
            for order, (name, concept_name) in enumerate(foundation_data, start=4):
                topic = Topic(chapter_id=foundation_chapter.id, name=name, display_order=order)
                session.add(topic)
                session.flush()
                session.add(Concept(topic_id=topic.id, name=concept_name, display_order=1))
                foundation_ids[name] = topic.id
            session.commit()

            migration_path = Path(__file__).parents[1] / "alembic" / "versions" / "20261007_0029_nda_gat_general_science_history_geography_current_events.py"
            spec = importlib.util.spec_from_file_location("nda_gat_general_knowledge_migration", migration_path)
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.loader)
            migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration)

            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
                migration.upgrade()

            session.expire_all()
            chapter_names = {
                chapter.name
                for chapter in session.scalars(select(Chapter).where(Chapter.subject_id == gat.id))
            }
            self.assertTrue({"General Science", "History", "Geography", "Current Events"}.issubset(chapter_names))
            for chapter_name, _ in foundation_data:
                chapter = session.scalar(
                    select(Chapter).where(Chapter.subject_id == gat.id, Chapter.name == chapter_name)
                )
                moved_foundation = session.get(Topic, foundation_ids[chapter_name])
                self.assertEqual(moved_foundation.chapter_id, chapter.id)
                self.assertEqual(moved_foundation.name, f"{chapter_name} Foundations")
            self.assertEqual(
                session.scalar(
                    select(func.count()).select_from(Topic).where(Topic.name == "Recent Events in India and the World")
                ),
                1,
            )
            self.assertEqual(
                session.scalar(
                    select(func.count()).select_from(Concept).where(Concept.name == "Rocks and their classification")
                ),
                1,
            )
            self.assertEqual(
                session.scalar(
                    select(func.count()).select_from(Concept).where(Concept.name == "Indian climate and natural vegetation")
                ),
                1,
            )
            self.assertEqual(
                session.scalar(select(func.count()).select_from(Topic)),
                21,
            )
            self.assertEqual(
                session.scalar(select(func.count()).select_from(Concept)),
                53,
            )

            with Operations.context(MigrationContext.configure(connection)):
                migration.downgrade()
            session.expire_all()
            for chapter_name, concept_name in foundation_data:
                restored_topic = session.get(Topic, foundation_ids[chapter_name])
                self.assertEqual(restored_topic.name, chapter_name)
                self.assertEqual(restored_topic.chapter_id, foundation_chapter.id)
                self.assertIsNotNone(
                    session.scalar(select(Concept).where(
                        Concept.topic_id == restored_topic.id,
                        Concept.name == concept_name,
                    ))
                )
            self.assertEqual(
                session.scalar(select(func.count()).select_from(Topic)),
                4,
            )
            session.close()

        engine.dispose()
