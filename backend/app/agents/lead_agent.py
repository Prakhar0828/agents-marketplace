"""Sales Lead Agent (web version).

Refactored from the CLI script at repo-root `lead_agent.py`. The scraping,
merging, and scoring logic is unchanged — only the surrounding orchestration
has been adapted so progress streams over a websocket via `emit(...)` instead
of being printed to a Rich console.
"""

from __future__ import annotations

import asyncio
import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable

from openai import OpenAI

from ..config import DOWNLOADS_DIR, MODEL
from ..mcp_client import LenientClientSession, call_tool

Emit = Callable[[dict], Awaitable[None]]


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class Lead:
    name: str
    platform: str  # "Google Maps" | "Instagram" | "Both"
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


# ── Helpers ──────────────────────────────────────────────────────────────────


def _extract_json(text: str) -> list | dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for pattern in (r"\[.*\]", r"\{.*\}"):
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


def _extract_intent(client: OpenAI, user_message: str, prior: dict | None) -> dict:
    """Parse a free-form message into structured search parameters.

    If `prior` is supplied (the previous partial intent), the LLM is told to
    merge the new message into it so follow-up answers ("Mumbai") slot into
    the missing field instead of overwriting niche.
    """
    system = (
        "Extract lead search intent from the user message. "
        "Return JSON with keys:\n"
        "  niche    (str | null)  — type of business\n"
        "  location (str | null)  — city or area\n"
        "  count    (int)         — how many leads, default 10\n"
        "  hashtags (list[str])   — 2-3 relevant Instagram hashtags without #"
    )
    if prior:
        system += (
            "\n\nThe user was previously asked for missing info. "
            f"Merge this response into the prior intent: {json.dumps(prior)}. "
            "Preserve existing non-null fields unless explicitly overridden."
        )

    resp = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
    )
    return json.loads(resp.choices[0].message.content)


# ── Scrapers ──────────────────────────────────────────────────────────────────


async def _scrape_google_maps(
    session: LenientClientSession,
    niche: str,
    location: str,
    count: int,
    emit: Emit,
) -> list[Lead]:
    await emit(
        {
            "type": "tool_call",
            "name": "compass--crawler-google-places",
            "args": {"query": f"{niche} in {location}", "count": count},
        }
    )
    raw = await call_tool(
        session,
        "compass--crawler-google-places",
        {
            "searchStringsArray": [f"{niche} in {location}"],
            "maxCrawledPlacesPerSearch": count,
            "language": "en",
        },
    )
    data = _extract_json(raw)
    if not isinstance(data, list):
        await emit(
            {
                "type": "tool_result",
                "name": "compass--crawler-google-places",
                "preview": "No results",
            }
        )
        return []

    leads: list[Lead] = []
    for item in data:
        if not item.get("title"):
            continue
        leads.append(
            Lead(
                name=item.get("title", "—"),
                platform="Google Maps",
                location=(
                    item.get("neighborhood")
                    or item.get("city")
                    or item.get("address")
                    or location
                ),
                phone=item.get("phone") or "—",
                website=item.get("website") or "—",
                rating=item.get("totalScore"),
                reviews=item.get("reviewsCount"),
            )
        )

    await emit(
        {
            "type": "tool_result",
            "name": "compass--crawler-google-places",
            "preview": f"Got {len(leads)} places",
        }
    )
    return leads


async def _scrape_instagram(
    session: LenientClientSession,
    hashtags: list[str],
    count: int,
    emit: Emit,
) -> list[Lead]:
    if not hashtags:
        return []

    await emit(
        {
            "type": "tool_call",
            "name": "apify--instagram-hashtag-scraper",
            "args": {"hashtags": hashtags, "resultsLimit": count * 3},
        }
    )
    raw_ht = await call_tool(
        session,
        "apify--instagram-hashtag-scraper",
        {"hashtags": hashtags, "resultsLimit": count * 3},
    )
    posts = _extract_json(raw_ht)
    if not isinstance(posts, list) or not posts:
        await emit(
            {
                "type": "tool_result",
                "name": "apify--instagram-hashtag-scraper",
                "preview": "No posts found",
            }
        )
        return []

    usernames = list({p.get("ownerUsername") for p in posts if p.get("ownerUsername")})[
        :count
    ]
    await emit(
        {
            "type": "tool_result",
            "name": "apify--instagram-hashtag-scraper",
            "preview": f"Found {len(usernames)} unique profiles",
        }
    )
    if not usernames:
        return []

    await emit(
        {
            "type": "tool_call",
            "name": "apify--instagram-profile-scraper",
            "args": {"usernames": usernames},
        }
    )
    raw_pr = await call_tool(
        session,
        "apify--instagram-profile-scraper",
        {"usernames": usernames},
    )
    profiles = _extract_json(raw_pr)
    if not isinstance(profiles, list):
        await emit(
            {
                "type": "tool_result",
                "name": "apify--instagram-profile-scraper",
                "preview": "No profile data returned",
            }
        )
        return []

    leads: list[Lead] = []
    for p in profiles:
        if not p.get("username"):
            continue
        leads.append(
            Lead(
                name=p.get("fullName") or f"@{p['username']}",
                platform="Instagram",
                location=(
                    p.get("city")
                    or (p.get("businessAddressJson") or {}).get("city")
                    or "—"
                ),
                website=p.get("externalUrl") or "—",
                instagram_handle=f"@{p['username']}",
                followers=p.get("followersCount"),
                bio=(p.get("biography") or "")[:300],
            )
        )

    await emit(
        {
            "type": "tool_result",
            "name": "apify--instagram-profile-scraper",
            "preview": f"Enriched {len(leads)} profiles",
        }
    )
    return leads


# ── Merge & score ─────────────────────────────────────────────────────────────


def _merge_leads(maps_leads: list[Lead], ig_leads: list[Lead]) -> list[Lead]:
    maps_by_site = {
        lead.website.lower().rstrip("/"): lead
        for lead in maps_leads
        if lead.website != "—"
    }
    merged = list(maps_leads)
    for ig in ig_leads:
        key = ig.website.lower().rstrip("/") if ig.website != "—" else None
        if key and key in maps_by_site:
            existing = maps_by_site[key]
            existing.platform = "Both"
            existing.instagram_handle = ig.instagram_handle
            existing.followers = ig.followers
            existing.bio = ig.bio
        else:
            merged.append(ig)
    return merged


def _score_leads(
    client: OpenAI, leads: list[Lead], niche: str, location: str
) -> list[Lead]:
    if not leads:
        return leads

    summaries = [
        {
            "index": i,
            "name": lead.name,
            "platform": lead.platform,
            "location": lead.location,
            "followers": lead.followers,
            "rating": lead.rating,
            "reviews": lead.reviews,
            "has_website": lead.website != "—",
            "has_phone": lead.phone != "—",
            "has_instagram": lead.instagram_handle != "—",
            "bio": lead.bio[:200],
        }
        for i, lead in enumerate(leads)
    ]

    resp = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a lead scoring expert.\n"
                    f"Target niche: {niche}. Target location: {location}.\n\n"
                    "Score each lead from 1.0 to 10.0 based on:\n"
                    "  • Niche relevance\n"
                    "  • Social proof (followers, rating, review count)\n"
                    "  • Business completeness (website + phone + Instagram)\n"
                    "  • Reach and engagement potential\n\n"
                    "Return JSON: "
                    '{"scores": [{"index": 0, "score": 8.5, "reason": "one line"}, ...]}'
                ),
            },
            {"role": "user", "content": json.dumps(summaries)},
        ],
    )

    result = json.loads(resp.choices[0].message.content)
    for item in result.get("scores", []):
        idx = item.get("index", -1)
        if 0 <= idx < len(leads):
            leads[idx].score = round(float(item["score"]), 1)
            leads[idx].score_reason = item.get("reason", "—")

    return sorted(leads, key=lambda l: l.score or 0, reverse=True)


def _save_csv(leads: list[Lead], niche: str, location: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = f"{niche}_{location}".lower().replace(" ", "_")
    filename = f"leads_{slug}_{timestamp}.csv"
    path = DOWNLOADS_DIR / filename

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Rank",
                "Business",
                "Platform",
                "Instagram Handle",
                "Location",
                "Phone",
                "Website",
                "Followers",
                "Rating",
                "Reviews",
                "Score",
                "Score Reason",
                "Bio",
            ]
        )
        for i, lead in enumerate(leads, 1):
            writer.writerow(
                [
                    i,
                    lead.name,
                    lead.platform,
                    lead.instagram_handle,
                    lead.location,
                    lead.phone,
                    lead.website,
                    lead.followers or "",
                    lead.rating or "",
                    lead.reviews or "",
                    lead.score or "",
                    lead.score_reason,
                    lead.bio,
                ]
            )

    return filename


# ── Public entrypoint ─────────────────────────────────────────────────────────


# A conversation-level state object lives on the websocket handler and is
# passed back in for follow-up messages. When the user first connects it's
# `{"intent": None, "awaiting": None}`; after we ask "Which city?" the next
# user message is treated as a direct answer to that field.
LeadState = dict[str, Any]


def new_state() -> LeadState:
    return {"intent": None, "awaiting": None}


async def run_lead_agent(
    user_message: str,
    session: LenientClientSession,
    openai_client: OpenAI,
    state: LeadState,
    emit: Emit,
    **_ignored: Any,
) -> None:
    """Process one user turn.

    The hybrid flow is implemented here: if the LLM-extracted intent is still
    missing `niche` or `location`, we emit an assistant_message asking for it
    and stash the partial intent on `state`. On the next turn the previous
    intent is merged with the new message.
    """
    await emit({"type": "status", "message": "Understanding your request…"})

    prior = state.get("intent")
    intent = _extract_intent(openai_client, user_message, prior)
    state["intent"] = intent

    niche = intent.get("niche")
    location = intent.get("location")
    count = int(intent.get("count") or 10)
    hashtags = intent.get("hashtags") or []

    if not niche:
        state["awaiting"] = "niche"
        await emit(
            {
                "type": "assistant_message",
                "text": "What type of business are you looking for? (e.g. yoga studios, dental clinics, cafes)",
            }
        )
        return
    if not location:
        state["awaiting"] = "location"
        await emit(
            {
                "type": "assistant_message",
                "text": f"Got it — {niche}. Which city or area should I search in?",
            }
        )
        return

    # Intent complete — reset awaiting flag and let the user know the plan.
    state["awaiting"] = None
    await emit(
        {
            "type": "intent",
            "niche": niche,
            "location": location,
            "count": count,
            "hashtags": hashtags,
        }
    )
    await emit(
        {
            "type": "assistant_message",
            "text": (
                f"Searching for **{count}** {niche} in **{location}**. "
                f"I'll check Google Maps and Instagram hashtags {hashtags or '(none)'} "
                f"and score the results."
            ),
        }
    )

    # Scrape both sources concurrently — same pattern as the CLI script.
    await emit(
        {"type": "status", "message": f"Scraping Google Maps and Instagram in parallel…"}
    )
    maps_leads, ig_leads = await asyncio.gather(
        _scrape_google_maps(session, niche, location, count, emit),
        _scrape_instagram(session, hashtags, count, emit),
    )

    await emit(
        {
            "type": "status",
            "message": f"Merging {len(maps_leads)} Maps + {len(ig_leads)} Instagram leads…",
        }
    )
    leads = _merge_leads(maps_leads, ig_leads)

    await emit({"type": "status", "message": f"Scoring {len(leads)} leads with GPT…"})
    leads = _score_leads(openai_client, leads, niche, location)

    filename = _save_csv(leads, niche, location)
    await emit(
        {
            "type": "leads_table",
            "rows": [asdict(lead) for lead in leads],
            "niche": niche,
            "location": location,
            "csv_url": f"/api/downloads/{filename}",
        }
    )
    await emit(
        {
            "type": "assistant_message",
            "text": (
                f"Done! Ranked **{len(leads)}** leads. "
                "Tell me another niche/city to run a new search, "
                "or refine this one (e.g. \"only show ones with >10k followers\")."
            ),
        }
    )
    # Clear intent so the next turn is treated as a fresh request.
    state["intent"] = None
