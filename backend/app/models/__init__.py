"""Import every ORM model so Alembic can discover the full metadata."""

from app.models.assessment import Assessment, AssessmentAttempt, AssessmentQuestion, AssessmentQuestionAssignment
from app.models.chat import ChatMessage, ChatSession
from app.models.content import ContentChunk, ContentDocument, Source
from app.models.curriculum import Chapter, Concept, Exam, Prerequisite, Subject, Topic
from app.models.learning import LearningProgress, LearningSession, StudentMastery
from app.models.notifications import AdminUser, Notification
from app.models.parent_progress_report import ParentProgressReport
from app.models.questions import Question, QuestionAnswer, QuestionAttempt, QuestionOption
from app.models.users import StudentProfile, User
from app.models.tutorials import TutorialResource
from app.models.study_planner import StudyPlanTask
from app.models.daily_review import DailyReviewAttempt, DailyReviewItem
from app.models.daily_vocabulary import DailyVocabularyAttempt
from app.models.ssb_guidance import DailySSBGuidance, SSBGuidanceMessage

__all__ = [
    "AdminUser", "Assessment", "AssessmentAttempt", "AssessmentQuestion", "AssessmentQuestionAssignment", "Chapter", "ChatMessage",
    "ChatSession", "Concept", "ContentChunk", "ContentDocument", "Exam", "LearningProgress",
    "LearningSession", "Prerequisite", "Question", "QuestionAnswer", "QuestionAttempt",
    "DailyReviewAttempt", "DailyReviewItem", "DailyVocabularyAttempt", "DailySSBGuidance", "SSBGuidanceMessage", "Notification", "ParentProgressReport", "QuestionOption", "Source", "StudentMastery", "StudentProfile", "StudyPlanTask", "Subject", "Topic", "TutorialResource", "User",
]
