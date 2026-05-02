"""Marketplace registry.

Keeps the public-facing metadata (shown on cards) and the runtime wiring
(handler + MCP actors + state factory) side by side. The routes layer reads
from this so adding a new agent is a one-dict-entry change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from openai import OpenAI

from .agents import lead_agent, media_agent, resume_agent
from .mcp_client import LEAD_ACTORS, MEDIA_ACTORS, RESUME_ACTORS, LenientClientSession
from .models import AgentCard

Handler = Callable[
    [str, LenientClientSession, OpenAI, dict, Callable[[dict], Awaitable[None]]],
    Awaitable[None],
]


@dataclass
class RegistryEntry:
    card: AgentCard
    actors: list[str]
    handler: Handler
    new_state: Callable[[], dict]
    greeting: str


REGISTRY: dict[str, RegistryEntry] = {
    "sales-lead": RegistryEntry(
        card=AgentCard(
            id="sales-lead",
            name="Sales Lead Agent",
            tagline="Find and score B2B leads from Google Maps + Instagram",
            description=(
                "Describe your ideal customer (niche + city) and I'll pull real "
                "businesses from Google Maps and matching Instagram profiles, "
                "merge duplicates, and score every lead with GPT. You'll get a "
                "ranked table and a downloadable CSV."
            ),
            accent="emerald",
            icon="target",
            mode="intent_once",
            capabilities=[
                "Google Maps scraping",
                "Instagram hashtag & profile lookup",
                "GPT-powered scoring",
                "CSV export",
            ],
        ),
        actors=LEAD_ACTORS,
        handler=lead_agent.run_lead_agent,
        new_state=lead_agent.new_state,
        greeting=(
            "Hi! I'm your Sales Lead Agent. Tell me the niche and city you're "
            "targeting — e.g. \"Find 15 yoga studios in Mumbai\" — and I'll pull "
            "a ranked list of leads."
        ),
    ),
    "media-analyser": RegistryEntry(
        card=AgentCard(
            id="media-analyser",
            name="Content Research Agent",
            tagline="Analyse YouTube & Instagram content with an agentic loop",
            description=(
                "Ask anything about a creator, hashtag, reel, or YouTube topic. "
                "I call the right Apify actor, analyse engagement trends, and "
                "summarise what's working. Conversational — keep asking follow-ups."
            ),
            accent="violet",
            icon="sparkles",
            mode="agentic_loop",
            capabilities=[
                "YouTube search & comment mining",
                "Instagram profile / reel / hashtag scraping",
                "Engagement & trend analysis",
                "Multi-turn follow-ups",
            ],
        ),
        actors=MEDIA_ACTORS,
        handler=media_agent.run_media_agent,
        new_state=media_agent.new_state,
        greeting=(
            "Hi! I'm your Content Research Agent. Ask me about any YouTube topic "
            "or Instagram profile/hashtag/reel and I'll pull live data and surface "
            "the insights."
        ),
    ),
    "resume-optimizer": RegistryEntry(
        card=AgentCard(
            id="resume-optimizer",
            name="AI Resume Optimizer",
            tagline="Tailor your resume to any LinkedIn job with one upload",
            description=(
                "Attach your resume as a PDF, tell me the job title and company, "
                "and I'll scrape the LinkedIn listing, rewrite your resume to "
                "match the role's language, and hand back editable Markdown "
                "and .docx files."
            ),
            accent="cyan",
            icon="file-text",
            mode="intent_once",
            capabilities=[
                "PDF resume parsing",
                "LinkedIn job scraping (bebity actor)",
                "GPT-tailored rewrite (keywords + bullets)",
                "Markdown + .docx export",
            ],
        ),
        actors=RESUME_ACTORS,
        handler=resume_agent.run_resume_agent,
        new_state=resume_agent.new_state,
        greeting=(
            "Hi! I'm your Resume Optimizer. Upload your resume (PDF) using the "
            "paperclip button below, and tell me the job title and company "
            "you're targeting — e.g. *Senior Backend Engineer at Stripe*."
        ),
    ),
}


def get_entry(agent_id: str) -> RegistryEntry | None:
    return REGISTRY.get(agent_id)


def list_cards() -> list[AgentCard]:
    return [entry.card for entry in REGISTRY.values()]
