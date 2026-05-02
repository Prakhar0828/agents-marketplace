"""Marketplace registry.

Keeps the public-facing metadata (shown on cards) and the runtime wiring
(handler + MCP actors + state factory) side by side. The routes layer reads
from this so adding a new agent is a one-dict-entry change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from openai import OpenAI

from .agents import competitor_agent, lead_agent, media_agent, resume_agent
from .mcp_client import (
    COMPETITOR_ACTORS,
    LEAD_ACTORS,
    MEDIA_ACTORS,
    RESUME_ACTORS,
    LenientClientSession,
)
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
            name="Sales Leads Finder Agent",
            tagline="Build a qualified prospect list for any niche in any city",
            description=(
                "Tell me your target market and location, and I'll find real "
                "businesses with contact details, social profiles, ratings, and "
                "reviews — then rank them by fit so you can focus on the "
                "highest-value prospects first. Download the full list as a CSV."
            ),
            accent="emerald",
            icon="target",
            mode="intent_once",
            capabilities=[
                "Local business discovery",
                "Contact & social profiles",
                "Automated lead scoring",
                "CSV export",
            ],
        ),
        actors=LEAD_ACTORS,
        handler=lead_agent.run_lead_agent,
        new_state=lead_agent.new_state,
        greeting=(
            "Hi! I'm your Sales Leads Finder. Tell me the niche and city you're "
            "targeting — e.g. \"Find 15 yoga studios in Mumbai\" — and I'll pull "
            "a ranked list of leads."
        ),
    ),
    "media-analyser": RegistryEntry(
        card=AgentCard(
            id="media-analyser",
            name="Content Research Agent",
            tagline="Understand what content is winning in your space",
            description=(
                "Curious what your competitors are posting, which topics trend, or "
                "how a creator's audience engages? Ask in plain English and get "
                "engagement breakdowns, top-performing content, and actionable "
                "insights you can use to plan your next campaign."
            ),
            accent="violet",
            icon="sparkles",
            mode="agentic_loop",
            capabilities=[
                "YouTube & Instagram research",
                "Engagement & trend analysis",
                "Top-performing content discovery",
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
    "competitor-analysis": RegistryEntry(
        card=AgentCard(
            id="competitor-analysis",
            name="Competitor Analysis Agent",
            tagline="Know exactly how your competitors price, position, and sell",
            description=(
                "Give me your competitors' names or websites and I'll map out "
                "their pricing, key features, market positioning, and more — "
                "side by side. Download the comparison as a CSV so your team "
                "can build a winning strategy."
            ),
            accent="amber",
            icon="crosshair",
            mode="intent_once",
            capabilities=[
                "Competitor website research",
                "Pricing & feature comparison",
                "Market positioning insights",
                "Downloadable comparison table",
            ],
        ),
        actors=COMPETITOR_ACTORS,
        handler=competitor_agent.run_competitor_agent,
        new_state=competitor_agent.new_state,
        greeting=(
            "Hi! I'm your Competitor Analysis Agent. Tell me which competitors "
            "you'd like to research — company names or URLs both work. "
            "For example: *\"Analyse stripe.com, lemonsqueezy.com, and paddle.com\"*"
        ),
    ),
    "resume-optimizer": RegistryEntry(
        card=AgentCard(
            id="resume-optimizer",
            name="AI Resume Optimizer",
            tagline="Land more interviews with a resume tailored to the exact role",
            description=(
                "Upload your resume and tell me the job title + company. I'll "
                "pull the real job description, rewrite your resume to match "
                "the role's language and keywords, and deliver an interview-ready "
                "version you can download instantly."
            ),
            accent="cyan",
            icon="file-text",
            mode="intent_once",
            capabilities=[
                "Resume parsing & analysis",
                "Job description matching",
                "Keyword-optimized rewrite",
                "Instant download (Markdown + Word)",
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
