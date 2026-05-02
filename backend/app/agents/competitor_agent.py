"""Competitor Analysis Agent.

Flow:
  1. User provides a list of competitor company names or website URLs.
  2. GPT extracts structured intent (companies + their URLs if provided).
  3. We crawl each competitor website using `apify/website-content-crawler`.
  4. GPT analyses the crawled content to extract: pricing tiers, key features,
     positioning, and other notable data points.
  5. Results are emitted as a `competitor_result` event with a downloadable CSV.
"""

from __future__ import annotations

import csv
import json
import re
import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable

from mcp.shared.exceptions import McpError
from openai import OpenAI

from ..config import DOWNLOADS_DIR, MODEL
from ..mcp_client import LenientClientSession, call_tool

Emit = Callable[[dict], Awaitable[None]]


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class Competitor:
    company: str
    url: str
    pricing: str
    features: str
    positioning: str
    tech_stack: str
    notable: str


@dataclass
class Intent:
    companies: list[dict[str, str]]  # [{"name": "Acme", "url": "https://..."}]


# ── State ─────────────────────────────────────────────────────────────────────


def new_state() -> dict:
    return {"phase": "idle"}


# ── Intent extraction ─────────────────────────────────────────────────────────


def _extract_intent(client: OpenAI, user_message: str) -> Intent:
    system = textwrap.dedent("""\
        You extract competitor companies from a user message.
        Return JSON: {"companies": [{"name": "Company Name", "url": "https://..."}]}
        If the user gives URLs, use those. If they only give names, infer the most
        likely homepage URL (e.g. "Stripe" -> "https://stripe.com").
        Always return at least one company. Return up to 5.
    """)
    resp = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
    )
    data = json.loads(resp.choices[0].message.content)
    companies = data.get("companies", [])
    return Intent(companies=companies)


# ── Website crawling ──────────────────────────────────────────────────────────


def _extract_json(text: str) -> list | dict | None:
    """Same multi-value JSON parser used in the resume agent."""
    if not text:
        return None
    decoder = json.JSONDecoder()
    values: list[Any] = []
    idx = 0
    n = len(text)
    while idx < n:
        while idx < n and text[idx] not in "{[":
            idx += 1
        if idx >= n:
            break
        try:
            value, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            idx += 1
            continue
        values.append(value)
        idx = end
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    flat: list[Any] = []
    for v in values:
        if isinstance(v, list):
            flat.extend(v)
        else:
            flat.append(v)
    return flat


async def _crawl_website(
    session: LenientClientSession,
    url: str,
    company_name: str,
    emit: Emit,
) -> str:
    """Crawl a competitor's website and return the combined text content."""
    inputs: dict[str, Any] = {
        "startUrls": [{"url": url}],
        "maxCrawlPages": 10,
        "crawlerType": "cheerio",
    }

    await emit(
        {
            "type": "tool_call",
            "name": "apify--website-content-crawler",
            "args": {"url": url, "company": company_name, "maxPages": 10},
        }
    )

    try:
        raw = await call_tool(session, "apify--website-content-crawler", inputs)
    except McpError as exc:
        await emit(
            {
                "type": "tool_result",
                "name": "apify--website-content-crawler",
                "preview": f"Crawl error: {exc}",
            }
        )
        return ""

    data = _extract_json(raw)
    pages: list[str] = []

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                text = item.get("text") or item.get("markdown") or item.get("body") or ""
                if text:
                    pages.append(text[:3000])
        await emit(
            {
                "type": "tool_result",
                "name": "apify--website-content-crawler",
                "preview": f"{len(pages)} page(s) crawled for {company_name}",
            }
        )
    elif isinstance(data, dict):
        text = data.get("text") or data.get("markdown") or data.get("body") or ""
        if text:
            pages.append(text[:3000])
        await emit(
            {
                "type": "tool_result",
                "name": "apify--website-content-crawler",
                "preview": f"1 page crawled for {company_name}",
            }
        )
    else:
        await emit(
            {
                "type": "tool_result",
                "name": "apify--website-content-crawler",
                "preview": f"No content extracted for {company_name}",
            }
        )

    return "\n\n---\n\n".join(pages)[:12000]


# ── GPT analysis ──────────────────────────────────────────────────────────────


ANALYSIS_SYSTEM_PROMPT = textwrap.dedent("""\
    You are a competitive intelligence analyst.

    Given website content from a company, extract:
    1. Pricing: Pricing tiers, plans, prices (say "Not found on website" if absent).
    2. Features: Key product features or service offerings (bullet-point list).
    3. Positioning: Their value proposition and target market.
    4. Tech Stack: Any mention of technologies used (if visible).
    5. Notable: Anything else interesting (team size, funding, integrations, clients).

    Be factual — only report what's actually in the content. Keep each field concise (1-3 sentences or a short list).

    Return JSON: {
      "pricing": "...",
      "features": "...",
      "positioning": "...",
      "tech_stack": "...",
      "notable": "..."
    }
""")


def _analyse_competitor(
    client: OpenAI,
    company_name: str,
    url: str,
    website_content: str,
) -> Competitor:
    if not website_content.strip():
        return Competitor(
            company=company_name,
            url=url,
            pricing="Could not crawl website",
            features="—",
            positioning="—",
            tech_stack="—",
            notable="—",
        )

    user_payload = json.dumps({
        "company": company_name,
        "url": url,
        "website_content": website_content[:10000],
    })
    resp = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ],
    )
    data = json.loads(resp.choices[0].message.content)
    return Competitor(
        company=company_name,
        url=url,
        pricing=data.get("pricing", "—"),
        features=data.get("features", "—"),
        positioning=data.get("positioning", "—"),
        tech_stack=data.get("tech_stack", "—"),
        notable=data.get("notable", "—"),
    )


# ── CSV export ────────────────────────────────────────────────────────────────


def _save_csv(competitors: list[Competitor]) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"competitor_analysis_{timestamp}.csv"
    path = DOWNLOADS_DIR / filename

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Company", "URL", "Pricing", "Key Features",
            "Positioning", "Tech Stack", "Notable",
        ])
        for c in competitors:
            writer.writerow([
                c.company, c.url, c.pricing, c.features,
                c.positioning, c.tech_stack, c.notable,
            ])

    return filename


# ── Main handler ──────────────────────────────────────────────────────────────


async def run_competitor_agent(
    user_message: str,
    session: LenientClientSession,
    openai_client: OpenAI,
    state: dict,
    emit: Emit,
    **_ignored: Any,
) -> None:
    if not user_message.strip():
        await emit(
            {
                "type": "assistant_message",
                "text": (
                    "Tell me which competitors you'd like me to analyse. "
                    "You can give me company names, URLs, or both — e.g. "
                    '"Analyse stripe.com, lemonsqueezy.com, and paddle.com"'
                ),
            }
        )
        return

    # 1) Extract intent
    await emit({"type": "status", "message": "Understanding your request…"})
    intent = _extract_intent(openai_client, user_message)

    if not intent.companies:
        await emit(
            {
                "type": "assistant_message",
                "text": (
                    "I couldn't identify any competitors from your message. "
                    "Please provide company names or website URLs."
                ),
            }
        )
        return

    names = [c["name"] for c in intent.companies]
    await emit(
        {
            "type": "assistant_message",
            "text": (
                f"Got it! I'll analyse **{len(intent.companies)}** competitor(s): "
                f"{', '.join(f'**{n}**' for n in names)}. "
                "Crawling their websites now…"
            ),
        }
    )

    # 2) Crawl each competitor's website
    competitors: list[Competitor] = []
    for company_info in intent.companies:
        name = company_info.get("name", "Unknown")
        url = company_info.get("url", "")
        if not url:
            continue

        await emit({"type": "status", "message": f"Crawling {name} ({url})…"})
        content = await _crawl_website(session, url, name, emit)

        # 3) Analyse with GPT
        await emit({"type": "status", "message": f"Analysing {name}'s data…"})
        competitor = _analyse_competitor(openai_client, name, url, content)
        competitors.append(competitor)

    if not competitors:
        await emit(
            {
                "type": "error",
                "message": "Couldn't crawl any competitor websites. Please check the URLs.",
            }
        )
        return

    # 4) Save CSV + emit result
    filename = _save_csv(competitors)
    await emit(
        {
            "type": "competitor_result",
            "rows": [asdict(c) for c in competitors],
            "csv_url": f"/api/downloads/{filename}",
        }
    )
    await emit(
        {
            "type": "assistant_message",
            "text": (
                f"Done! I've analysed **{len(competitors)}** competitor(s). "
                "The comparison table is above with a CSV download. "
                "Want me to dig deeper into any specific competitor or compare "
                "specific aspects (like pricing only)?"
            ),
        }
    )
