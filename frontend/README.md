# NDA Chatbot – Frontend

React + TypeScript + Vite + Tailwind CSS frontend for the NDA Chatbot platform.

## Phase 10 Status

- Vite + React + TypeScript setup
- Tailwind CSS configured
- Authenticated workspace with curriculum, chat, diagnostic, learning and mastery flows
- Weekly NDA mocks with 50 Mathematics and 50 General Ability questions; full-length mocks with 120 Mathematics and 150 General Ability questions
- Weekly section timers of 30 minutes and full-length section timers of 2.5 hours; monthly mocks pause between Mathematics and GAT and must be completed the same day
- Four-option MCQs with Previous/Next navigation, saved selections, final Submit with unanswered questions allowed, and a confirmed Skip exam action that cancels without a score or report
- Randomized question selection and NDA-style one-third negative marking
- AI-generated questions are labeled in the mock and require an enabled backend AI provider when the published question bank runs short
- Vite proxy for `/api` → `http://localhost:8000`
- English or Hindi speech-to-text input in chat (browser microphone permission required); tutor responses remain text
- Registration requests private student and guardian profile photos, optional student phone, required parent WhatsApp number, and guardian consent

## Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Run development server:
```bash
npm run dev
```

For trusted local HTTPS on Windows, install mkcert, then from the `frontend` directory run:

```powershell
New-Item -ItemType Directory -Force .cert | Out-Null
mkcert -install
mkcert -cert-file .cert/localhost.pem -key-file .cert/localhost-key.pem localhost 127.0.0.1 ::1
npm.cmd run dev
```

Install mkcert with `winget install --id FiloSottile.mkcert -e`, then open a new PowerShell window before running the commands above. If PowerShell blocks `npm.ps1`, use `npm.cmd`.

3. Open browser:
- https://localhost:5173 (when the trusted mkcert certificate is installed; otherwise Vite warns and uses HTTP)

The application calls the backend health endpoint and shows the connection state.
Keep `.cert` private and local; its key is ignored by Git and must not be shared.
