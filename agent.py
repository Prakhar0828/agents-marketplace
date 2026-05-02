"""
Media Analyser Agent
Connects to the Apify MCP server for YouTube and Instagram scraping,
backed by OpenAI GPT-4o as the reasoning engine.
"""

import asyncio
import json
import os
import sys
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
MODEL           = "gpt-5.4"

# Actors to expose — keeps the tool list focused and fast to load.
# Add or remove actor slugs from https://apify.com/store as needed.
APIFY_ACTORS = [
    "streamers/youtube-scraper",       # primary YouTube actor
    "apify/instagram-scraper",
    "apify/instagram-post-scraper",
    "apify/instagram-reel-scraper",
    "apify/instagram-hashtag-scraper",
    "apify/instagram-profile-scraper",
]

APIFY_MCP_URL = (
    f"https://mcp.apify.com/sse"
    f"?token={APIFY_API_TOKEN}"
    f"&actors={','.join(APIFY_ACTORS)}"
)

# Passed to every request (SSE stream + POST messages) so the server
# accepts both the initial connection and subsequent tool calls.
APIFY_HEADERS = {"Authorization": f"Bearer {APIFY_API_TOKEN}"}

SYSTEM_PROMPT = """You are a media analysis AI agent with access to live web-scraping tools
powered by Apify. You can retrieve real data from YouTube and Instagram.

Tool names and their purpose:
  • streamers--youtube-scraper     → search YouTube videos/channels, fetch video details & comments
  • apify--instagram-scraper       → general Instagram scraping (profiles, posts, hashtags)
  • apify--instagram-post-scraper  → scrape specific Instagram posts
  • apify--instagram-reel-scraper  → scrape Instagram reels
  • apify--instagram-hashtag-scraper → scrape posts under a hashtag
  • apify--instagram-profile-scraper → scrape an Instagram profile

IMPORTANT: always pick the tool that matches the platform in the user's request.
  - YouTube queries → use streamers--youtube-scraper only
  - Instagram queries → use the relevant instagram-* tool

Workflow guidelines:
  1. Call the most appropriate Apify tool with sensible defaults.
  2. After receiving raw data, summarise and analyse it — highlight trends, top performers,
     engagement rates, or anything the user would find actionable.
  3. If a scrape returns a large dataset, surface the top 5–10 items and offer to go deeper.
  4. Always be transparent: mention how many items were fetched and any obvious data gaps.
  5. Never fabricate data — if a tool call fails, say so and suggest alternatives."""

console = Console()

# ── Lenient MCP session ───────────────────────────────────────────────────────

class LenientClientSession(ClientSession):
    """
    Apify's actor output schemas sometimes use non-standard JSON Schema types
    (e.g. "unknown") that cause mcp>=1.6 strict validation to crash.
    This subclass silently skips output-schema validation so those actors still work.
    """
    async def _validate_tool_result(self, name: str, result: Any) -> None:
        pass


# ── Helpers ──────────────────────────────────────────────────────────────────

def validate_env() -> None:
    missing = []
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not APIFY_API_TOKEN:
        missing.append("APIFY_API_TOKEN")
    if missing:
        console.print(
            f"[bold red]Missing environment variables:[/bold red] {', '.join(missing)}\n"
            "Copy [cyan].env.example[/cyan] to [cyan].env[/cyan] and fill in your keys."
        )
        sys.exit(1)


def mcp_tools_to_openai(tools) -> list[dict[str, Any]]:
    """Convert MCP tool definitions to OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema,
            },
        }
        for t in tools
    ]


async def call_tool(session: LenientClientSession, name: str, arguments: dict) -> str:
    """Execute an MCP tool and return its text output."""
    result = await session.call_tool(name, arguments)
    parts = [item.text for item in result.content if hasattr(item, "text")]
    return "\n".join(parts) if parts else "(tool returned no text content)"


# ── Agent loop ────────────────────────────────────────────────────────────────

async def run_agent(
    session: LenientClientSession,
    openai_client: OpenAI,
    tools: list[dict],
    conversation: list[dict],
) -> str:
    """
    Agentic loop: send messages → handle tool calls → repeat until the model
    returns a plain text response with no further tool calls.

    OpenAI tool-call format:
      assistant message  →  role="assistant", tool_calls=[...]
      tool result        →  role="tool",      tool_call_id=..., content=...
    """
    while True:
        response = openai_client.chat.completions.create(
            model=MODEL,
            tools=tools,
            messages=conversation,
        )

        choice = response.choices[0]
        message = choice.message

        # Always append the raw assistant message to keep history consistent
        conversation.append(message.to_dict())

        if choice.finish_reason == "tool_calls":
            for tc in message.tool_calls:
                console.print(
                    f"\n  [dim]▶ Calling tool:[/dim] [cyan]{tc.function.name}[/cyan]"
                )

                arguments = json.loads(tc.function.arguments)

                with console.status("[dim]Waiting for Apify...[/dim]", spinner="dots"):
                    raw_result = await call_tool(session, tc.function.name, arguments)

                preview = raw_result[:300].replace("\n", " ")
                console.print(f"  [dim]◀ Result preview:[/dim] {preview}…\n")

                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": raw_result,
                    }
                )

        else:
            # finish_reason == "stop" — plain text final answer
            return message.content or ""


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    validate_env()

    console.print(
        Panel.fit(
            "[bold cyan]Media Analyser Agent[/bold cyan]\n"
            "[dim]YouTube & Instagram · Powered by Apify MCP + GPT-5.4[/dim]",
            border_style="cyan",
        )
    )

    try:
        async with sse_client(APIFY_MCP_URL, headers=APIFY_HEADERS) as (read, write):
            async with LenientClientSession(read, write) as session:
                await session.initialize()

                with console.status("Fetching tool list…", spinner="dots"):
                    raw_tools = (await session.list_tools()).tools
                    tools     = mcp_tools_to_openai(raw_tools)

                console.print(
                    f"[green]✓[/green] Connected — [bold]{len(tools)}[/bold] Apify tools loaded\n"
                )

                if tools:
                    console.print("[dim]Available actors:[/dim]")
                    for t in tools:
                        console.print(f"  [cyan]•[/cyan] {t['function']['name']}")
                    console.print()

                openai_client = OpenAI(api_key=OPENAI_API_KEY)
                conversation: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

                console.print(Rule("[dim]Chat — type [bold]quit[/bold] to exit[/dim]"))

                while True:
                    try:
                        user_input = console.input("\n[bold green]You:[/bold green] ").strip()
                    except (EOFError, KeyboardInterrupt):
                        console.print("\n[dim]Goodbye![/dim]")
                        break

                    if not user_input:
                        continue
                    if user_input.lower() in {"quit", "exit", "q"}:
                        console.print("[dim]Goodbye![/dim]")
                        break

                    conversation.append({"role": "user", "content": user_input})

                    with console.status("Agent thinking…", spinner="dots"):
                        reply = await run_agent(
                            session, openai_client, tools, conversation
                        )

                    console.print("\n[bold blue]Agent:[/bold blue]")
                    console.print(Markdown(reply))

    except Exception as exc:
        console.print(f"\n[bold red]Fatal error:[/bold red] {exc}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
