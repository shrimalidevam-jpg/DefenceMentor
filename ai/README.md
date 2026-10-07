# AI Module

This folder documents the LLM provider boundary and future RAG pipeline.

Phase 12 adds the provider boundary in `backend/app/services/ai_provider.py` and a context-aware chat completion API.

For a completely zero-cost setup with no model download, keep `AI_PROVIDER=disabled`. The deterministic curriculum, learning-path, mastery and assessment features remain fully available, and chat messages can still be saved without generated AI replies.

Gemini's free tier is available through `AI_PROVIDER=gemini-free` with a dedicated `GEMINI_FREE_API_KEY`. Keep billing disabled on the Google project: the app uses a fixed model, does not retry quota errors, and has no paid-provider fallback, but cannot inspect or control project billing. Local Ollama is also available through `AI_PROVIDER=ollama` and is restricted to loopback addresses.

The deterministic curriculum, learning-path, mastery and assessment services remain authoritative; the LLM only generates tutor language.

Phase 13 now provides verified source/chunk ingestion and deterministic retrieval. Only administrator-reviewed sources marked verified are passed into tutor prompts. Embeddings, vector search and automated document ingestion remain future optimization work.