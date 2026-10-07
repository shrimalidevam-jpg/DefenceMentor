"""Authenticated chat-session and message persistence endpoints for Phase 6."""

import base64
import binascii
import json
import re
from io import BytesIO
from collections import defaultdict
from urllib.parse import quote, urlsplit
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, WebSocket, WebSocketDisconnect, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.core.security import decode_access_token
from app.models.chat import ChatMessage, ChatSession
from app.models.users import User
from app.schemas.chat import (
    ChatDocumentSource,
    ChatCompletionResponse,
    ChatAttachmentUpload,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionDetailResponse,
    ChatSessionResponse,
    ChatSessionUpdate,
)
from app.services.ai_provider import AIProviderError, AIProviderQuotaExceeded, AIProviderUnavailable, get_ai_provider
from app.services.rag_retriever import retrieve_chunks
from app.services.tutor_orchestrator import orchestrate_tutor_turn


router = APIRouter(prefix="/chats", tags=["Chat"])

MAX_CHAT_ATTACHMENT_BYTES = 4 * 1024 * 1024
MAX_CHAT_ATTACHMENT_TOTAL_BYTES = 10 * 1024 * 1024
MAX_CHAT_ATTACHMENT_COUNT = 3

TUTOR_SYSTEM_PROMPT = """You are a personal teacher and NDA preparation tutor for a student studying from their current level toward NDA exam readiness. Your goal is to help the student understand and become able to solve problems, not merely give answers.

Answer the student's latest request and use recent conversation context to understand follow-ups. Follow the student's most recent explicit language request even when it differs from the language they used to write; otherwise match their language and writing system. Never assume their level: infer it from their question and demonstrated work. For a simple factual request, answer directly and briefly. For a new or difficult concept, build from intuition and any actually missing prerequisite, then explain the concept with a worked example and a small practice/check question when useful. Ask at most one focused diagnostic question at a time, only when the answer would change how you teach; do not turn every conversation into an interview or withhold a requested explanation behind a gate. Remember demonstrated strengths, weak areas and misconceptions from this conversation; do not repeatedly reteach mastered basics.

Adapt explanation depth: use plain language and concrete examples for beginners; focus on application, patterns, common traps and efficient NDA methods for prepared students. Teach the sound reasoning before shortcuts. Explain each symbol and why a formula works. In mathematics, show the given information, method, intermediate steps and a reasonableness check. If the student is wrong, diagnose whether the issue is conceptual, prerequisite, method, reading or arithmetic; explain the specific correction supportively and offer an easier retry when helpful. If the student is confused, change the example or approach instead of repeating the same explanation. Increase practice difficulty gradually and do not assume understanding from a short acknowledgement.

Keep responses clear, accurate and proportional to the question; use Markdown headings, short paragraphs, and numbered steps or bullets when they make the explanation easier to scan. Avoid textbook dumps, unnecessary sections and excessive quizzes. Write equations in readable plain text (for example, "P(E) = favourable outcomes / total possible outcomes"); do not use LaTeX dollar delimiters or raw LaTeX commands. Never shame the student. Do not invent facts, syllabus details, statistics, formulas, answers, or previous-year questions. Claim a question is an actual NDA past-paper question only when verified material explicitly establishes that. Prefer relevant retrieved educational material when provided; do not invent citations or claim to have browsed. Never provide Google search or YouTube links. The application attaches verified topic document links separately when relevant sources are available. State uncertainty for facts you cannot verify, especially time-sensitive current affairs. Deterministic application services control learning paths, mastery and assessment decisions."""


class ChatConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, session_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[session_id].add(websocket)

    def disconnect(self, session_id: UUID, websocket: WebSocket) -> None:
        connections = self.connections.get(session_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            self.connections.pop(session_id, None)

    async def broadcast(self, session_id: UUID, payload: dict[str, object]) -> None:
        stale_connections: list[WebSocket] = []
        for websocket in self.connections.get(session_id, set()).copy():
            try:
                await websocket.send_json(payload)
            except Exception:
                stale_connections.append(websocket)
        for websocket in stale_connections:
            self.disconnect(session_id, websocket)


connection_manager = ChatConnectionManager()


def _topic_document_links(retrieved_sources: list[dict]) -> list[ChatDocumentSource]:
    """Keep only relevant, verified, direct document URLs for the chat UI."""
    links: list[ChatDocumentSource] = []
    seen_documents: set[UUID] = set()
    for source in retrieved_sources:
        raw_url = source.get("url")
        if not raw_url or float(source.get("relevance_score") or 0) < 0.25:
            continue
        parsed = urlsplit(str(raw_url))
        host = (parsed.hostname or "").casefold().removeprefix("www.")
        if parsed.scheme not in {"http", "https"} or not host:
            continue
        if host == "youtu.be" or host.endswith("youtube.com"):
            continue
        if (host.startswith("google.") or host.endswith(".google.com")) and parsed.path.startswith("/search"):
            continue
        if parsed.path in {"", "/"}:
            continue
        document_id = source["document_id"]
        if document_id in seen_documents:
            continue
        seen_documents.add(document_id)
        links.append(ChatDocumentSource(
            source_id=source["source_id"],
            document_id=document_id,
            title=str(source["title"]),
            url=str(raw_url),
            page_reference=source.get("page_reference"),
            relevance_score=float(source["relevance_score"]),
        ))
        if len(links) == 3:
            break
    return links


def _is_disallowed_link(url: str) -> bool:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").casefold().removeprefix("www.")
    return (
        host == "youtu.be"
        or host.endswith("youtube.com")
        or ((host.startswith("google.") or host.endswith(".google.com")) and parsed.path.startswith("/search"))
    )


def _remove_disallowed_links(content: str) -> str:
    markdown_link = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", re.IGNORECASE)
    content = markdown_link.sub(lambda match: "" if _is_disallowed_link(match.group(2)) else match.group(0), content)
    raw_url = re.compile(r"https?://[^\s<>()\]]+", re.IGNORECASE)
    return raw_url.sub(lambda match: "" if _is_disallowed_link(match.group(0).rstrip(".,;!?")) else match.group(0), content)


def automatic_chat_title(content: str) -> str:
    """Create a short, deterministic title from the first user message."""
    title = " ".join(content.split()).strip(" .?!")
    title = re.sub(
        r"^(please|can you|could you|help me|i want to learn|i want to know|explain|teach me|tell me about|what is|how do i|how to)\s+",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"^(i do not understand|i don't understand|i am struggling with|i'm struggling with)\s+", "", title, flags=re.IGNORECASE)
    words = title.split()
    if len(words) > 8:
        title = " ".join(words[:8]) + "..."
    return (title[:157] + "...") if len(title) > 160 else title


def set_automatic_title(chat_session: ChatSession, content: str) -> None:
    if chat_session.title.strip().casefold() in {"new chat", "new conversation"}:
        chat_session.title = automatic_chat_title(content) or "New chat"


def get_owned_session(database: Session, session_id: UUID, user_id: UUID) -> ChatSession:
    chat_session = database.scalar(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    if chat_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    return chat_session


@router.post("", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_chat(
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> ChatSession:
    chat_session = ChatSession(
        user_id=current_user.id,
        title=payload.title.strip(),
        subject_id=payload.subject_id,
        topic_id=payload.topic_id,
        current_concept_id=payload.current_concept_id,
        learning_state="started",
    )
    database.add(chat_session)
    database.commit()
    database.refresh(chat_session)
    return chat_session


@router.post("/draft", response_model=ChatSessionResponse, status_code=status.HTTP_200_OK)
def get_or_create_chat_draft(
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> ChatSession:
    """Reuse the user's newest empty draft and discard older empty drafts."""
    empty_chats = list(database.scalars(
        select(ChatSession)
        .where(
            ChatSession.user_id == current_user.id,
            ~exists().where(ChatMessage.chat_session_id == ChatSession.id),
        )
        .order_by(ChatSession.updated_at.desc())
    ))
    if empty_chats:
        draft = empty_chats[0]
        for unused_draft in empty_chats[1:]:
            database.delete(unused_draft)
        if len(empty_chats) > 1:
            database.commit()
            database.refresh(draft)
        return draft

    draft = ChatSession(user_id=current_user.id, title="New chat", learning_state="started")
    database.add(draft)
    database.commit()
    database.refresh(draft)
    return draft


@router.get("", response_model=list[ChatSessionResponse])
def list_chats(
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> list[ChatSession]:
    return list(
        database.scalars(
            select(ChatSession)
            .where(
                ChatSession.user_id == current_user.id,
                exists().where(ChatMessage.chat_session_id == ChatSession.id),
            )
            .order_by(ChatSession.updated_at.desc())
        )
    )


@router.get("/{session_id}", response_model=ChatSessionDetailResponse)
def read_chat(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> ChatSessionDetailResponse:
    chat_session = get_owned_session(database, session_id, current_user.id)
    messages = list(
        database.scalars(
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == session_id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
    )
    return ChatSessionDetailResponse.model_validate(
        {**chat_session.__dict__, "messages": messages}, from_attributes=True
    )


@router.patch("/{session_id}", response_model=ChatSessionResponse)
def rename_chat(
    session_id: UUID,
    payload: ChatSessionUpdate,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> ChatSession:
    chat_session = get_owned_session(database, session_id, current_user.id)
    chat_session.title = payload.title.strip()
    database.commit()
    database.refresh(chat_session)
    return chat_session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> None:
    chat_session = get_owned_session(database, session_id, current_user.id)
    database.delete(chat_session)
    database.commit()


@router.post("/{session_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
def add_message(
    session_id: UUID,
    payload: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> ChatMessage:
    chat_session = get_owned_session(database, session_id, current_user.id)
    if payload.attachments:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Use the tutor completion endpoint to send files.")
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message content cannot be empty.")
    next_sequence = database.scalar(
        select(func.coalesce(func.max(ChatMessage.sequence_number), 0) + 1).where(
            ChatMessage.chat_session_id == chat_session.id
        )
    )
    message = ChatMessage(chat_session_id=chat_session.id, role="user", content=content, sequence_number=next_sequence)
    database.add(message)
    set_automatic_title(chat_session, message.content)
    chat_session.learning_state = "message_received"
    database.commit()
    database.refresh(message)
    return message


def _validate_chat_attachments(uploads: list[ChatAttachmentUpload]) -> list[dict[str, object]]:
    if len(uploads) > MAX_CHAT_ATTACHMENT_COUNT:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Attach no more than three files per message.")

    attachments: list[dict[str, object]] = []
    total_size = 0
    for upload in uploads:
        try:
            data = base64.b64decode(upload.data_base64, validate=True)
        except (binascii.Error, ValueError) as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{upload.file_name} is not valid base64 file data.") from error
        if not data or len(data) > MAX_CHAT_ATTACHMENT_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"Each attachment must be smaller than 4 MB: {upload.file_name}.")
        total_size += len(data)
        if total_size > MAX_CHAT_ATTACHMENT_TOTAL_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Attachments must total 10 MB or less.")

        media_type = upload.media_type
        if media_type == "application/pdf":
            if not data.startswith(b"%PDF-"):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{upload.file_name} is not a valid PDF.")
        else:
            try:
                with Image.open(BytesIO(data)) as image:
                    image_format = image.format
                    if image.width * image.height > 20_000_000:
                        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{upload.file_name} exceeds the 20-megapixel image limit.")
                    image.verify()
                actual_media_type = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(image_format or "")
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{upload.file_name} is not a valid supported image.") from error
            if actual_media_type != media_type:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"The detected image format for {upload.file_name} does not match its file type.")

        file_name = re.split(r"[\\/]", upload.file_name)[-1]
        file_name = re.sub(r"[\x00-\x1f\x7f]", "", file_name).strip()[:180] or "attachment"
        attachments.append({
            "id": str(uuid4()),
            "file_name": file_name,
            "media_type": media_type,
            "size": len(data),
            "data_base64": base64.b64encode(data).decode("ascii"),
        })
    return attachments


@router.post("/{session_id}/messages/complete", response_model=ChatCompletionResponse, status_code=status.HTTP_201_CREATED)
def complete_message(
    session_id: UUID,
    payload: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> ChatCompletionResponse:
    """Persist a user message and ask the configured provider for a tutor response."""
    attachments = _validate_chat_attachments(payload.attachments)
    chat_session = get_owned_session(database, session_id, current_user.id)
    current_learning_state = chat_session.learning_state
    content = payload.content.strip()
    if not content and not attachments:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter a message or attach a file.")
    next_sequence = database.scalar(select(func.coalesce(func.max(ChatMessage.sequence_number), 0) + 1).where(ChatMessage.chat_session_id == chat_session.id))
    if attachments and not content:
        content = "Please explain the attached file."
    user_message = ChatMessage(chat_session_id=chat_session.id, role="user", content=content, sequence_number=next_sequence, attachments=attachments)
    database.add(user_message)
    set_automatic_title(chat_session, content)
    database.flush()
    history = list(database.scalars(select(ChatMessage).where(ChatMessage.chat_session_id == chat_session.id).order_by(ChatMessage.sequence_number)))
    conversation_history = [{"role": item.role, "content": item.content} for item in history]
    tutor_turn = orchestrate_tutor_turn(content, conversation_history, current_learning_state)
    recent_attachment_message_ids = {
        item.id
        for item in [
            message
            for message in reversed(history)
            if message.role == "user" and message.attachments
        ][:2]
    }
    provider_messages: list[dict[str, object]] = [
        {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
        {"role": "system", "content": "Only when the student explicitly requests a visual for a learning topic, return a valid Mermaid flowchart inside one ```mermaid fenced block. Keep labels concise and relationships accurate. Never output SVG or HTML, and do not add diagram code to ordinary replies."},
        {"role": "system", "content": tutor_turn.guidance},
        *[
            {
                "role": item.role if item.role in {"user", "assistant", "system"} else "user",
                "content": item.content,
                **({"attachments": item.attachments} if item.id in recent_attachment_message_ids else {}),
            }
            for item in history[-12:]
        ],
    ]
    if attachments:
        if tutor_turn.fixed_response:
            tutor_turn = type(tutor_turn)(
                guidance=tutor_turn.guidance + " The student attached a file. Analyze its relevant content and answer their question; do not redirect them away from it.",
                next_state="ai_response",
            )
            provider_messages[2]["content"] = tutor_turn.guidance
    if payload.oral_explanation:
        provider_messages.insert(
            1,
            {
                "role": "system",
                "content": (
                    "The student requested an oral explanation. Explain naturally as a supportive teacher speaking "
                    "to the student: use short sentences, conversational transitions, and verbal descriptions of "
                    "formulas and symbols. Avoid Markdown headings, tables, bullet lists, code blocks, and LaTeX "
                    "because the response will be read aloud. Follow the student's most recent explicit language "
                    "request, even if it differs from the language they wrote in, and fully answer the "
                    "question without unnecessary length."
                ),
            },
        )
    previous_user_message = next((item.content for item in reversed(history[:-1]) if item.role == "user"), None)
    is_short_follow_up = bool(re.match(r"^(why|how|what about|which one|more|continue|explain more|tell me more|give an example|example)\b", content, re.IGNORECASE))
    retrieval_query = f"{previous_user_message} {content}" if previous_user_message and is_short_follow_up else content
    social_messages = {"hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "bye"}
    retrieved_sources = [] if content.casefold().strip(" .!?") in social_messages else retrieve_chunks(database, retrieval_query, chat_session.topic_id, limit=5)
    document_links = _topic_document_links(retrieved_sources)
    if retrieved_sources:
        provider_messages.insert(1, {"role": "system", "content": "Verified educational context:\n" + "\n\n".join(f"[{item['title']}] {item['content']}" for item in retrieved_sources)})
    try:
        assistant_content = tutor_turn.fixed_response or _remove_disallowed_links(get_ai_provider().generate(provider_messages))
    except AIProviderQuotaExceeded as error:
        database.rollback()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(error)) from error
    except AIProviderUnavailable as error:
        database.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except AIProviderError as error:
        database.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    assistant_message = ChatMessage(
        chat_session_id=chat_session.id,
        role="assistant",
        content=assistant_content,
        sequence_number=next_sequence + 1,
        sources=[source.model_dump(mode="json") for source in document_links],
    )
    database.add(assistant_message)
    chat_session.learning_state = tutor_turn.next_state or "ai_response"
    database.commit()
    database.refresh(user_message)
    database.refresh(assistant_message)
    return ChatCompletionResponse(user_message=user_message, assistant_message=assistant_message, chat_title=chat_session.title, provider=settings.AI_PROVIDER, sources=document_links)


@router.get("/{session_id}/messages/{message_id}/attachments/{attachment_id}")
def download_chat_attachment(
    session_id: UUID,
    message_id: UUID,
    attachment_id: UUID,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
) -> Response:
    get_owned_session(database, session_id, current_user.id)
    message = database.scalar(
        select(ChatMessage).where(
            ChatMessage.id == message_id,
            ChatMessage.chat_session_id == session_id,
            ChatMessage.role == "user",
        )
    )
    attachment = next(
        (item for item in (message.attachments if message else []) if item.get("id") == str(attachment_id)),
        None,
    )
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat attachment not found.")
    try:
        data = base64.b64decode(attachment["data_base64"], validate=True)
    except (KeyError, binascii.Error, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="The saved chat attachment could not be read.") from error
    file_name = quote(str(attachment["file_name"]), safe="")
    return Response(
        content=data,
        media_type=str(attachment["media_type"]),
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{file_name}"},
    )


@router.websocket("/{session_id}/ws")
async def chat_websocket(websocket: WebSocket, session_id: UUID, token: str | None = None) -> None:
    """Authenticate a browser WebSocket and persist/broadcast realtime chat events."""
    if not token:
        await websocket.close(code=1008, reason="Authentication is required")
        return
    payload = decode_access_token(token)
    if payload is None or not isinstance(payload.get("sub"), str):
        await websocket.close(code=1008, reason="Invalid access token")
        return
    try:
        user_id = UUID(payload["sub"])
    except ValueError:
        await websocket.close(code=1008, reason="Invalid access token")
        return

    database = SessionLocal()
    try:
        chat_session = database.scalar(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        if chat_session is None:
            await websocket.close(code=1008, reason="Chat session not found")
            return
        await connection_manager.connect(session_id, websocket)
        await websocket.send_json({"type": "connected", "session_id": str(session_id)})
        try:
            while True:
                raw_event = await websocket.receive_text()
                try:
                    event = json.loads(raw_event)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "error": "Event must be valid JSON"})
                    continue
                event_type = event.get("type")
                if event_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif event_type == "typing":
                    await connection_manager.broadcast(session_id, {"type": "typing", "is_typing": bool(event.get("is_typing"))})
                elif event_type == "message":
                    content = event.get("content")
                    if not isinstance(content, str) or not content.strip() or len(content) > 10000:
                        await websocket.send_json({"type": "error", "error": "Message must contain 1-10000 characters"})
                        continue
                    next_sequence = database.scalar(
                        select(func.coalesce(func.max(ChatMessage.sequence_number), 0) + 1).where(
                            ChatMessage.chat_session_id == session_id
                        )
                    )
                    message = ChatMessage(chat_session_id=session_id, role="user", content=content.strip(), sequence_number=next_sequence)
                    database.add(message)
                    set_automatic_title(chat_session, message.content)
                    chat_session.learning_state = "message_received"
                    database.commit()
                    database.refresh(message)
                    await connection_manager.broadcast(session_id, {"type": "message", "message": {"id": str(message.id), "chat_session_id": str(message.chat_session_id), "role": message.role, "content": message.content, "sources": message.sources or [], "created_at": message.created_at.isoformat(), "updated_at": message.updated_at.isoformat()}})
                else:
                    await websocket.send_json({"type": "error", "error": "Unsupported event type"})
        except WebSocketDisconnect:
            pass
    finally:
        connection_manager.disconnect(session_id, websocket)
        database.close()
