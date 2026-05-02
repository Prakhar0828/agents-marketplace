"""
Lead Scraping Agent
Scrapes leads from Google Maps and Instagram, scores them with GPT-5.4,
and displays a ranked table in the terminal.
"""

import asyncio
import csv
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
MODEL           = "gpt-5.4"

APIFY_ACTORS = [
    "compass/crawler-google-places",
    "apify/instagram-hashtag-scraper",
    "apify/instagram-profile-scraper",
]

APIFY_MCP_URL = (
    f"https://mcp.apify.com/sse"
    f"?token={APIFY_API_TOKEN}"
    f"&actors={','.join(APIFY_ACTORS)}"
)

APIFY_HEADERS = {"Authorization": f"Bearer {APIFY_API_TOKEN}"}

console = Console()

# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Lead:
    name: str
    platform: str               # "Google Maps" | "Instagram" | "Both"
    location: str = "—"
    phone: str    = "—"
    website: str  = "—"
    instagram_handle: str = "—"
    followers: int | None   = None
    rating:    float | None = None
    reviews:   int | None   = None
    bio: str = ""
    score: float | None = None
    score_reason: str   = "—"


# ── Lenient MCP session ───────────────────────────────────────────────────────

class LenientClientSession(ClientSession):
    """Skip strict output-schema validation — some Apify actors use non-standard types."""
    async def _validate_tool_result(self, name: str, result: Any) -> None:
        pass


# ── Helpers ──────────────────────────────────────────────────────────────────

def validate_env() -> None:
    missing = [k for k, v in [("OPENAI_API_KEY", OPENAI_API_KEY),
                                ("APIFY_API_TOKEN", APIFY_API_TOKEN)] if not v]
    if missing:
        console.print(f"[bold red]Missing env vars:[/bold red] {', '.join(missing)}")
        sys.exit(1)


def extract_json(text: str) -> list | dict | None:
    """Extract the first valid JSON array or object from a mixed-text response."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for pattern in (r'\[.*\]', r'\{.*\}'):
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


async def call_tool(session: LenientClientSession, name: str, inputs: dict) -> str:
    result = await session.call_tool(name, inputs)
    parts = [item.text for item in result.content if hasattr(item, "text")]
    return "\n".join(parts) if parts else ""


# ── Intent extraction ─────────────────────────────────────────────────────────

def extract_intent(client: OpenAI, user_message: str) -> dict:
    """Parse a free-form query into structured search parameters."""
    resp = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract lead search intent from the user message. "
                    "Return JSON with keys:\n"
                    "  niche    (str | null)  — type of business\n"
                    "  location (str | null)  — city or area\n"
                    "  count    (int)         — how many leads, default 10\n"
                    "  hashtags (list[str])   — 2-3 relevant Instagram hashtags without #"
                ),
            },
            {"role": "user", "content": user_message},
        ],
    )
    return json.loads(resp.choices[0].message.content)


# ── Scrapers ──────────────────────────────────────────────────────────────────

async def scrape_google_maps(
    session: LenientClientSession, niche: str, location: str, count: int
) -> list[Lead]:
    with console.status(f"[dim]Google Maps → {niche} in {location}…[/dim]", spinner="dots"):
        raw = await call_tool(
            session,
            "compass--crawler-google-places",
            {
                "searchStringsArray": [f"{niche} in {location}"],
                "maxCrawledPlacesPerSearch": count,
                "language": "en",
            },
        )

    data = extract_json(raw)
    if not isinstance(data, list):
        console.print("  [yellow]⚠[/yellow]  Google Maps — no results")
        return []

    leads = []
    for item in data:
        if not item.get("title"):
            continue
        leads.append(Lead(
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
        ))
    return leads


async def scrape_instagram(
    session: LenientClientSession, hashtags: list[str], count: int
) -> list[Lead]:
    if not hashtags:
        return []

    # Step 1 — discover usernames via hashtag posts
    with console.status(f"[dim]Instagram hashtags → {hashtags}…[/dim]", spinner="dots"):
        raw_ht = await call_tool(
            session,
            "apify--instagram-hashtag-scraper",
            {"hashtags": hashtags, "resultsLimit": count * 3},
        )

    posts = extract_json(raw_ht)
    if not isinstance(posts, list) or not posts:
        console.print("  [yellow]⚠[/yellow]  Instagram hashtags — no posts found")
        return []

    usernames = list({p.get("ownerUsername") for p in posts if p.get("ownerUsername")})[:count]
    if not usernames:
        return []

    # Step 2 — fetch full profile details for discovered accounts
    with console.status(f"[dim]Instagram profiles → {len(usernames)} accounts…[/dim]", spinner="dots"):
        raw_pr = await call_tool(
            session,
            "apify--instagram-profile-scraper",
            {"usernames": usernames},
        )

    profiles = extract_json(raw_pr)
    if not isinstance(profiles, list):
        console.print("  [yellow]⚠[/yellow]  Instagram profiles — no data returned")
        return []

    leads = []
    for p in profiles:
        if not p.get("username"):
            continue
        leads.append(Lead(
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
        ))
    return leads


# ── Merge & deduplicate ───────────────────────────────────────────────────────

def merge_leads(maps_leads: list[Lead], ig_leads: list[Lead]) -> list[Lead]:
    """
    If the same website appears in both sources, collapse into one 'Both' lead
    instead of showing two rows for the same business.
    """
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
            existing.platform         = "Both"
            existing.instagram_handle = ig.instagram_handle
            existing.followers        = ig.followers
            existing.bio              = ig.bio
        else:
            merged.append(ig)

    return merged


# ── Lead scoring ──────────────────────────────────────────────────────────────

def score_leads(client: OpenAI, leads: list[Lead], niche: str, location: str) -> list[Lead]:
    if not leads:
        return leads

    summaries = [
        {
            "index":        i,
            "name":         l.name,
            "platform":     l.platform,
            "location":     l.location,
            "followers":    l.followers,
            "rating":       l.rating,
            "reviews":      l.reviews,
            "has_website":  l.website != "—",
            "has_phone":    l.phone != "—",
            "has_instagram": l.instagram_handle != "—",
            "bio":          l.bio[:200],
        }
        for i, l in enumerate(leads)
    ]

    with console.status("[dim]GPT-5.4 scoring leads…[/dim]", spinner="dots"):
        resp = client.chat.completions.create(
            model=MODEL,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a lead scoring expert.\n"
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
            leads[idx].score        = round(float(item["score"]), 1)
            leads[idx].score_reason = item.get("reason", "—")

    return sorted(leads, key=lambda l: l.score or 0, reverse=True)


# ── Table rendering ───────────────────────────────────────────────────────────

PLATFORM_COLOUR = {
    "Google Maps": "green",
    "Instagram":   "magenta",
    "Both":        "cyan bold",
}


def render_table(leads: list[Lead], niche: str, location: str) -> None:
    table = Table(
        title=f"[bold cyan]Top Leads — {niche} in {location}[/bold cyan]",
        header_style="bold magenta",
        border_style="dim",
        row_styles=["", "dim"],
        show_lines=False,
        expand=False,
    )

    table.add_column("#",          width=3,  justify="right", style="bold")
    table.add_column("Business",   width=24)
    table.add_column("Platform",   width=12)
    table.add_column("Handle",     width=18)
    table.add_column("Location",   width=18)
    table.add_column("Phone",      width=14)
    table.add_column("Followers",  width=10, justify="right")
    table.add_column("Rating",     width=7,  justify="right")
    table.add_column("Score",      width=6,  justify="right")
    table.add_column("Why",        min_width=30)

    for i, lead in enumerate(leads, 1):
        colour = PLATFORM_COLOUR.get(lead.platform, "white")

        if lead.score is None:
            score_str = "—"
        elif lead.score >= 7:
            score_str = f"[bold green]{lead.score}[/bold green]"
        elif lead.score >= 5:
            score_str = f"[yellow]{lead.score}[/yellow]"
        else:
            score_str = f"[red]{lead.score}[/red]"

        table.add_row(
            str(i),
            lead.name[:24],
            f"[{colour}]{lead.platform}[/{colour}]",
            lead.instagram_handle,
            lead.location[:18],
            lead.phone,
            f"{lead.followers:,}" if lead.followers else "—",
            f"{lead.rating}★"     if lead.rating    else "—",
            score_str,
            lead.score_reason,
        )

    both_count = sum(1 for l in leads if l.platform == "Both")

    console.print()
    console.print(table)
    console.print(
        f"\n[dim]{len(leads)} leads · "
        f"{sum(1 for l in leads if l.platform == 'Google Maps')} from Maps · "
        f"{sum(1 for l in leads if l.platform == 'Instagram')} from Instagram · "
        f"{both_count} matched on both[/dim]"
    )


# ── CSV export ───────────────────────────────────────────────────────────────

def save_csv(leads: list[Lead], niche: str, location: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug      = f"{niche}_{location}".lower().replace(" ", "_")
    filename  = f"leads_{slug}_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Rank", "Business", "Platform", "Instagram Handle",
            "Location", "Phone", "Website",
            "Followers", "Rating", "Reviews",
            "Score", "Score Reason", "Bio",
        ])
        for i, lead in enumerate(leads, 1):
            writer.writerow([
                i,
                lead.name,
                lead.platform,
                lead.instagram_handle,
                lead.location,
                lead.phone,
                lead.website,
                lead.followers or "",
                lead.rating    or "",
                lead.reviews   or "",
                lead.score     or "",
                lead.score_reason,
                lead.bio,
            ])

    return filename


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    validate_env()

    console.print(
        Panel.fit(
            "[bold cyan]Lead Scraping Agent[/bold cyan]\n"
            "[dim]Google Maps + Instagram · Scored by GPT-5.4[/dim]",
            border_style="cyan",
        )
    )

    openai_client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        async with sse_client(APIFY_MCP_URL, headers=APIFY_HEADERS) as (read, write):
            async with LenientClientSession(read, write) as session:
                await session.initialize()

                with console.status("Fetching tool list…", spinner="dots"):
                    raw_tools = (await session.list_tools()).tools

                console.print(
                    f"[green]✓[/green] Connected — [bold]{len(raw_tools)}[/bold] tools loaded\n"
                )

                console.print(Rule("[dim]Describe the leads you want · type [bold]quit[/bold] to exit[/dim]"))
                console.print("[dim]Example: 'Find 15 yoga studios in Mumbai'[/dim]\n")

                while True:
                    try:
                        user_input = console.input("[bold green]You:[/bold green] ").strip()
                    except (EOFError, KeyboardInterrupt):
                        console.print("\n[dim]Goodbye![/dim]")
                        break

                    if not user_input:
                        continue
                    if user_input.lower() in {"quit", "exit", "q"}:
                        console.print("[dim]Goodbye![/dim]")
                        break

                    # Extract niche / location / hashtags from free-form input
                    with console.status("Understanding your request…", spinner="dots"):
                        intent = extract_intent(openai_client, user_input)

                    niche    = intent.get("niche")
                    location = intent.get("location")
                    count    = int(intent.get("count") or 10)
                    hashtags = intent.get("hashtags") or []

                    if not niche:
                        console.print("[yellow]What type of business are you looking for?[/yellow]")
                        continue
                    if not location:
                        console.print("[yellow]Which city or area should I search in?[/yellow]")
                        continue

                    console.print(
                        f"\n  [dim]Niche:[/dim] [bold]{niche}[/bold]  "
                        f"[dim]Location:[/dim] [bold]{location}[/bold]  "
                        f"[dim]Count:[/dim] {count}  "
                        f"[dim]Hashtags:[/dim] {hashtags}\n"
                    )

                    # Scrape both sources concurrently
                    maps_leads, ig_leads = await asyncio.gather(
                        scrape_google_maps(session, niche, location, count),
                        scrape_instagram(session, hashtags, count),
                    )

                    console.print(
                        f"\n  [green]✓[/green] Google Maps: {len(maps_leads)} leads  "
                        f"[green]✓[/green] Instagram: {len(ig_leads)} leads"
                    )

                    leads = merge_leads(maps_leads, ig_leads)
                    leads = score_leads(openai_client, leads, niche, location)
                    render_table(leads, niche, location)

                    path = save_csv(leads, niche, location)
                    console.print(f"[green]✓[/green] Saved to [bold]{path}[/bold]")

    except Exception as exc:
        console.print(f"\n[bold red]Fatal error:[/bold red] {exc}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
