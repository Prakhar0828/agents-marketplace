"""Apify MCP session helpers.

The same lenient-validation + SSE connection logic that the CLI scripts use,
repackaged as an async context manager so every WebSocket chat session gets
its own isolated MCP connection.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from mcp import ClientSession
from mcp.client.sse import sse_client

from .config import APIFY_API_TOKEN

# Actor slugs exposed to each agent. Keeping them union-merged here means the
# frontend doesn't need to know which tools belong to which agent — the LLM
# selects based on the system prompt.
LEAD_ACTORS = [
    "compass/crawler-google-places",
    "apify/instagram-hashtag-scraper",
    "apify/instagram-profile-scraper",
]

MEDIA_ACTORS = [
    "streamers/youtube-scraper",
    "apify/instagram-scraper",
    "apify/instagram-post-scraper",
    "apify/instagram-reel-scraper",
    "apify/instagram-hashtag-scraper",
    "apify/instagram-profile-scraper",
]

# The Resume Optimizer just needs a LinkedIn jobs scraper. Keeping it on its
# own keeps tool-discovery fast and the LLM context focused.
RESUME_ACTORS = [
    "bebity/linkedin-jobs-scraper",
]


class LenientClientSession(ClientSession):
    """Skip strict output-schema validation — Apify actors use non-standard types."""

    async def _validate_tool_result(self, name: str, result: Any) -> None:  # type: ignore[override]
        pass


def _mcp_url(actors: list[str]) -> str:
    return (
        "https://mcp.apify.com/sse"
        f"?token={APIFY_API_TOKEN}"
        f"&actors={','.join(actors)}"
    )


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {APIFY_API_TOKEN}"}


@asynccontextmanager
async def apify_session(actors: list[str]) -> AsyncIterator[LenientClientSession]:
    """Open a lenient MCP session against Apify's SSE endpoint.

    Usage:
        async with apify_session(LEAD_ACTORS) as session:
            tools = (await session.list_tools()).tools
            ...
    """
    async with sse_client(_mcp_url(actors), headers=_headers()) as (read, write):
        async with LenientClientSession(read, write) as session:
            await session.initialize()
            yield session


async def call_tool(
    session: LenientClientSession, name: str, inputs: dict[str, Any]
) -> str:
    """Invoke an MCP tool and flatten its text output."""
    result = await session.call_tool(name, inputs)
    parts = [item.text for item in result.content if hasattr(item, "text")]
    return "\n".join(parts) if parts else ""
