"""API contracts for Phase 6 chat sessions and messages."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreate(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=160)
    subject_id: UUID | None = None
    topic_id: UUID | None = None
    current_concept_id: UUID | None = None


class ChatSessionUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=160)


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    subject_id: UUID | None
    topic_id: UUID | None
    learning_state: str | None
    current_concept_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ChatAttachmentUpload(BaseModel):
    file_name: str = Field(min_length=1, max_length=180)
    media_type: str = Field(pattern=r"^(image/(jpeg|png|webp)|application/pdf)$")
    data_base64: str = Field(min_length=1, max_length=5_600_000)


class ChatMessageCreate(BaseModel):
    content: str = Field(max_length=10000)
    oral_explanation: bool = False
    attachments: list[ChatAttachmentUpload] = Field(default_factory=list, max_length=3)


class ChatDocumentSource(BaseModel):
    source_id: UUID
    document_id: UUID
    title: str
    url: str
    page_reference: str | None = None
    relevance_score: float


class ChatAttachmentResponse(BaseModel):
    id: UUID
    file_name: str
    media_type: str
    size: int


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_session_id: UUID
    role: str
    content: str
    sources: list[ChatDocumentSource] = Field(default_factory=list)
    attachments: list[ChatAttachmentResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ChatCompletionResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    chat_title: str = "New chat"
    provider: str
    sources: list[ChatDocumentSource] = Field(default_factory=list)


class ChatSessionDetailResponse(ChatSessionResponse):
    messages: list[ChatMessageResponse] = Field(default_factory=list)
