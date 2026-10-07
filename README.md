# NDA Chatbot

**NDA Chatbot: An AI-Driven Adaptive Learning and Assessment Platform for Personalized NDA Examination Preparation**

This is a production-quality MSc IT (AI-ML) project that provides personalized, adaptive learning and assessment for NDA exam preparation.

## Phase 13 – Verified RAG Tutor (Current)

Implemented through Phase 10:

- Project folder structure
- React + TypeScript + Vite + Tailwind frontend
- FastAPI + Pydantic backend
- NDA Mathematics curriculum chapters and syllabus topics across algebra, matrices, trigonometry, analytical geometry, calculus, vectors, statistics and probability
- NDA GAT English curriculum covering spotting errors, comprehension, word selection, synonyms, antonyms, sentence improvement and sentence ordering
- NDA GAT Physics and Chemistry curriculum covering the syllabus topics and concepts
- NDA GAT General Science, History, Geography and Current Events curriculum based on the supplied syllabus
- Dedicated SSB guidance with the 15 Officer Like Qualities, one AI-generated daily action, and a private SSB/personality-development coaching chat
- Environment configuration
- Health-check API (`GET /api/health`)
- JWT authentication, curriculum hierarchy and prerequisite graph
- Authenticated chat UI/WebSocket transport
- Diagnostic assessment, personalized learning sessions and practice
- Configurable mastery scoring using difficulty, time, hints, confidence and recency
- Four-round adaptive assessment: Easy, Medium, Hard and General
- Optional local Ollama tutor; cloud AI providers are disabled to prevent API charges
- Admin-reviewed source ingestion and verified keyword retrieval for grounded tutor context
- English/Hindi tutor responses that honor an explicit language request regardless of the student's message language, browser-based voice-to-text chat input, on-demand spoken replies, and an optional oral-explanation mode that asks the AI for speech-friendly answers
- Chat uploads for up to three photos/images or PDF documents per message; uploads are retained with the conversation and sent to the configured AI tutor for analysis
- Student and guardian profile photos, optional student phone, required guardian WhatsApp number, and recorded guardian consent
- Opt-in weekly and monthly WhatsApp progress reports (requires WhatsApp Business Cloud API configuration)

**Not included yet:** vector embeddings, admin content management and deployment automation.

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.12
- Node.js 18+
- PostgreSQL 14+

### 1. Backend (Windows PowerShell)

```bash
cd D:\NDA-Chatbot\backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend will run at: **http://localhost:8000**

- Health: http://localhost:8000/api/health
- Docs:  http://localhost:8000/docs

### 2. Frontend (open a second terminal)

Install mkcert once and trust its local development CA:

```powershell
winget install --id FiloSottile.mkcert -e
```

After installation, open a new PowerShell window and run:

```powershell
cd D:\NDA-Chatbot\frontend
New-Item -ItemType Directory -Force .cert | Out-Null
mkcert -install
mkcert -cert-file .cert/localhost.pem -key-file .cert/localhost-key.pem localhost 127.0.0.1 ::1
npm.cmd install
npm.cmd run dev
```

Frontend will run at: **https://localhost:5173**. Vite uses HTTPS when the trusted local certificate exists; otherwise it prints a warning and runs on HTTP.

The certificate and private key are local-only, ignored by Git, and must not be shared or included in project ZIPs. The backend remains on loopback HTTP; browser API and WebSocket traffic goes through Vite's HTTPS proxy.

Open the browser. You should see a green “Backend is Online” message with the health response.

---

### AI tutor setup

The API starts without an AI provider, but tutor answers require a provider. To use Gemini, add a Gemini API key to `backend/.env` and set:

```dotenv
AI_PROVIDER=gemini-free
GEMINI_FREE_API_KEY=your-key
```

Image and PDF chat analysis is supported by Gemini. The local Ollama provider can analyze images when using a vision-capable model, but PDF attachments require Gemini. Chat accepts JPEG, PNG, WebP, and PDF files up to 4 MB each, with at most three files and 10 MB combined. Attachments are stored with the chat message in the database and are removed when the conversation is deleted. Run `python -m alembic upgrade head` after updating to add the chat attachment column.

Alternatively, install and run Ollama locally and configure `AI_PROVIDER=ollama` and `AI_MODEL` in `backend/.env`. Do not commit `.env` or API keys.

For production deployments, set `APP_ENV=production`, `DEBUG=false`, and a unique random `SECRET_KEY` of at least 32 characters. The API rejects insecure production settings and disables interactive API documentation in production.

## Vercel deployment (frontend only)

The React/Vite frontend can be published on Vercel as a static site:

1. Import `https://github.com/shrimalidevam-jpg/DefenceMentor` into Vercel.
2. Set **Root Directory** to `frontend`.
3. Keep the build command as `npm run build` and output directory as `dist`. The included `frontend/vercel.json` configures these and the client-side route fallback.
4. Leave `VITE_API_URL` unset for a frontend-only deployment. Set `VITE_GOOGLE_CLIENT_ID` only if Google sign-in has been configured.
5. Deploy.

**Important:** this publishes the user interface only. Authentication, health status, chat, learning data, AI tutoring, and other API-backed features require the FastAPI backend and PostgreSQL database; they will not work in a Vercel-only static deployment. The live chat also uses WebSockets, which Vercel Functions do not support. Do not put API keys, database URLs, or other secrets in `VITE_*` variables; those values are exposed in the browser bundle.

Do not commit `.env` files, database URLs, OAuth secrets, AI keys, or generated local certificates.

### Parent WhatsApp reports

New registrations require student and guardian profile photos, a parent/guardian WhatsApp number in international format (for example `+919876543210`), and a parent/legal guardian consent checkbox. The student's own phone is optional. Photos are stored as private profile data; the application does not perform face recognition. Report consent can be withdrawn from Profile settings.

To enable automated reports, configure `WHATSAPP_ACCESS_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID` in `backend/.env`. Create and have Meta approve a WhatsApp Business Cloud API template named by `WHATSAPP_TEMPLATE_NAME` (default `nda_progress_report`) with three body placeholders, in order: student name, report period, and progress summary. Set its language with `WHATSAPP_TEMPLATE_LANGUAGE`. Reports are scheduled for Sunday and the last day of each month at 18:00 in `APP_TIMEZONE` (default `Asia/Kolkata`). Reports are not sent until a valid WhatsApp Business configuration and approved template are provided.

### Google sign-in setup (free)

Create a Google OAuth **Web application** client ID, add `https://localhost:5173` as an authorized JavaScript origin (and `http://localhost:5173` only if you also use the HTTP fallback), then set that same ID in both `frontend/.env` (`VITE_GOOGLE_CLIENT_ID`) and `backend/.env` (`GOOGLE_CLIENT_ID`). Restart both development servers after changing the environment files. Google sign-in is hidden until the frontend client ID is configured.

## Expected Health Response

```json
{
  "status": "ok",
  "service": "NDA Chatbot API"
}
```

---

## Project Structure

```
NDA-Chatbot/
├── frontend/          # React + TypeScript + Vite + Tailwind
├── backend/           # FastAPI + SQLAlchemy + Alembic
├── database/          # Future: SQL scripts, seeds
├── ai/                # Future: LLM providers, RAG
├── docs/              # Documentation
├── tests/             # Future: tests
├── README.md
└── .gitignore
```

---

## Development Phases Overview

| Phase | Focus                          | Status     |
|-------|--------------------------------|------------|
| 1     | Foundation (this release)      | ✅ Done    |
| 2     | Database models & migrations   | ✅ Done    |
| 3     | Authentication (JWT)           | ✅ Done    |
| 4     | Curriculum structure           | ✅ Done    |
| 5     | Knowledge graph                | ✅ Done    |
| 6-7   | Chat UI + WebSocket            | ✅ Done    |
| 8     | Diagnostic engine              | ✅ Done    |
| 9     | Personalized learning          | ✅ Done    |
| 10    | Mastery engine                 | ✅ Done    |
| 11    | Adaptive examination           | ✅ Done    |
| 12    | AI/LLM integration             | ✅ Done    |
| 13    | RAG                            | ✅ Done    |
| 14    | Admin panel                    | Skipped / optional |
| 14-16 | Admin, Testing, Deployment     | Pending    |

---

## Important Notes

- Do **not** put secrets or API keys in the frontend.
- All configuration is done via `.env` files.
- PostgreSQL is required for the normal local application configuration.
- AI / LLM will be added only from Phase 12 onwards.

---

## License

Academic / Educational project.
