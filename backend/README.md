# NDA Chatbot – Backend

FastAPI backend for the NDA Chatbot adaptive learning platform.

## Phase 13 Status

- FastAPI health, authentication, curriculum, chat, diagnostic, learning and mastery APIs
- JWT authentication and role authorization
- Google sign-in through Google Identity Services (free Google OAuth web client)
- PostgreSQL SQLAlchemy models with migrations through Phase 10
- Prerequisite graph and transparent mastery scoring
- Adaptive examination API with performance-based round selection
- Timed weekly and full-length NDA mock assessments, randomized four-option MCQs and NDA-style negative marking
- Optional provider-based AI tutor completion; disabled safely without configuration
- Guided teach-back tutoring: the tutor checks whether a student has tried a topic, asks what they understand or find confusing, and corrects misconceptions supportively
- Verified source/chunk ingestion for administrators and deterministic retrieval for tutor context
- Full NDA Mathematics chapter and syllabus hierarchy, seeded by Alembic migration
- NDA GAT English chapter and syllabus topics, seeded by Alembic migration
- NDA GAT Physics and Chemistry syllabus chapters, topics and concepts, seeded by Alembic migration
- NDA GAT General Science, History, Geography and Current Events (current affairs) syllabus topics and concepts, seeded by Alembic migration
- Daily personalized SSB coaching guidance and a separate authenticated SSB/personality-development chat

## Setup

1. Create a virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy environment file (already created as `.env` for development):
```bash
# Edit .env if needed (especially DATABASE_URL)
```

4. Run the server:
```bash
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

AI is disabled by default. To use Gemini's free tier, set `AI_PROVIDER=gemini-free`, put a rotated AI Studio key in `GEMINI_FREE_API_KEY`, and ensure the Google project has no billing account linked. The app uses only `gemini-3.5-flash-lite`, makes one request per reply, and returns HTTP 429 on quota exhaustion without retries or paid-provider fallback. The app cannot verify the billing status of a Google project; linking billing can enable paid usage. Alternatively, use local Ollama with `AI_PROVIDER=ollama`. The AI provider only generates conversational language; curriculum, mastery and assessment decisions remain deterministic.

For production, set `APP_ENV=production`, `DEBUG=false`, and a unique `SECRET_KEY` of at least 32 characters. Production settings reject the development key, debug mode, and wildcard CORS, and disable interactive API documentation. The development server binds to loopback by default.

RAG endpoints:

```text
POST /api/rag/sources       # administrator only; reviewed source and chunks
GET  /api/rag/search        # authenticated; verified-source retrieval
```

Only sources marked as verified are included in retrieval and AI prompts.
No admin frontend is planned; administrators can manage reviewed sources through the protected API or a trusted script.

## NDA mock assessments

Weekly mocks contain 25 Mathematics and 25 General Ability Test questions, with a 15-minute timer for each section. Full-length mocks contain 120 Mathematics and 150 General Ability Test questions, with a 2.5-hour timer for each section. After Mathematics, a monthly mock pauses; the student must explicitly start GAT. Monthly mocks must be completed on the same India Standard Time calendar day. Questions support Previous/Next navigation, selected answers are saved while navigating, and the final Submit action permits unanswered questions. Students can also Skip exam to cancel an in-progress attempt; cancelled attempts have no score or report. Correct answers earn 2.5 marks in Mathematics or 4 marks in GAT; incorrect answers lose one-third of those marks, and unanswered questions receive no marks.

Questions are randomized from published four-option questions in the relevant subject. If the bank has no eligible question for a subject, the API generates an NDA-style question using the configured AI provider, saves it in the published bank, and labels it as AI-generated. AI is disabled by default; configure `AI_PROVIDER` and its provider settings in `.env` before relying on generation. Generation errors are returned instead of silently substituting a question.

5. Open in browser:
- Health: http://localhost:8000/api/health
- Docs: http://localhost:8000/docs

## Database migration

After starting PostgreSQL and configuring `DATABASE_URL` in `.env`:

```bash
cd backend
python -m alembic upgrade head
```

Run schema tests without PostgreSQL:

```bash
python -m unittest discover -s tests
```

## Authentication (Phase 3)

The API now provides registration, JWT login, current-user and profile endpoints under `/api/auth`.
Use `Authorization: Bearer <access_token>` for protected requests. The `/api/auth/admin/me` endpoint
requires a user with the `admin` role.

Promote an already-registered user only from a trusted local shell:

```bash
python -m scripts.create_admin admin@example.com
```

## Expected Health Response

```json
{
  "status": "ok",
  "service": "NDA Chatbot API"
}
```
