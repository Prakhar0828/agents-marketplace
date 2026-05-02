"""Pydantic models shared between routes and the frontend."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class AgentCard(BaseModel):
    """Public-facing metadata for a marketplace card."""

    id: str
    name: str
    tagline: str
    description: str
    accent: str  # Tailwind accent keyword: "emerald", "violet", ...
    icon: str  # lucide-react icon name
    mode: Literal["intent_once", "agentic_loop"]
    capabilities: list[str]


class Lead(BaseModel):
    name: str
    platform: str
    location: str = "—"
    phone: str = "—"
    website: str = "—"
    instagram_handle: str = "—"
    followers: int | None = None
    rating: float | None = None
    reviews: int | None = None
    bio: str = ""
    score: float | None = None
    score_reason: str = "—"


# ── WebSocket event union ─────────────────────────────────────────────────────
# All events share a `type` discriminator so the TS frontend can narrow safely.


class UserMessageEvent(BaseModel):
    type: Literal["user_message"] = "user_message"
    text: str


class AssistantMessageEvent(BaseModel):
    type: Literal["assistant_message"] = "assistant_message"
    text: str


class StatusEvent(BaseModel):
    type: Literal["status"] = "status"
    message: str


class ToolCallEvent(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    name: str
    args: dict[str, Any]


class ToolResultEvent(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    name: str
    preview: str


class IntentEvent(BaseModel):
    type: Literal["intent"] = "intent"
    niche: str | None = None
    location: str | None = None
    count: int | None = None
    hashtags: list[str] = []


class LeadsTableEvent(BaseModel):
    type: Literal["leads_table"] = "leads_table"
    rows: list[Lead]
    niche: str
    location: str
    csv_url: str | None = None


class ResumeResultEvent(BaseModel):
    """Final deliverable from the Resume Optimizer — rendered markdown plus
    downloadable `.md` and `.docx` URLs."""

    type: Literal["resume_result"] = "resume_result"
    job_title: str
    company: str
    markdown: str
    md_url: str
    docx_url: str
    summary: str = ""  # one-paragraph summary of what changed


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str


ChatEvent = (
    UserMessageEvent
    | AssistantMessageEvent
    | StatusEvent
    | ToolCallEvent
    | ToolResultEvent
    | IntentEvent
    | LeadsTableEvent
    | ResumeResultEvent
    | DoneEvent
    | ErrorEvent
)
