"""Content Research / Media Analyser Agent (web version).

Refactored from the CLI script at repo-root `agent.py`. Uses the same OpenAI
tool-calling loop, but every assistant turn and tool invocation is streamed
to the websocket via `emit(...)` so the frontend can render a live progress
timeline alongside the chat transcript.
"""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from openai import OpenAI

from ..config import MODEL
from ..mcp_client import LenientClientSession, call_tool

Emit = Callable[[dict], Awaitable[None]]


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
  5. Never fabricate data — if a tool call fails, say so and suggest alternatives.
  6. If the user's request is ambiguous (missing platform, topic, timeframe), ask one
     concise clarifying question before calling tools."""


def _mcp_tools_to_openai(tools) -> list[dict[str, Any]]:
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


MediaState = dict[str, Any]


def new_state() -> MediaState:
    return {"conversation": [{"role": "system", "content": SYSTEM_PROMPT}], "tools": None}


async def ensure_tools(session: LenientClientSession, state: MediaState) -> list[dict]:
    """Fetch Apify tool definitions once per websocket session."""
    if state.get("tools") is None:
        raw_tools = (await session.list_tools()).tools
        state["tools"] = _mcp_tools_to_openai(raw_tools)
    return state["tools"]


async def run_media_agent(
    user_message: str,
    session: LenientClientSession,
    openai_client: OpenAI,
    state: MediaState,
    emit: Emit,
    **_ignored: Any,
) -> None:
    """Run one user turn through the agentic tool-calling loop.

    The loop is identical to the CLI's `run_agent` at `agent.py:128` — we send
    the conversation to OpenAI, and whenever the model asks for tool calls we
    execute them against Apify and append the results until the model returns
    a plain-text answer.
    """
    tools = await ensure_tools(session, state)
    conversation: list[dict] = state["conversation"]
    conversation.append({"role": "user", "content": user_message})

    await emit({"type": "status", "message": "Agent thinking…"})

    while True:
        response = openai_client.chat.completions.create(
            model=MODEL,
            tools=tools,
            messages=conversation,
        )
        choice = response.choices[0]
        message = choice.message
        conversation.append(message.to_dict())

        if choice.finish_reason == "tool_calls":
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {"_raw": tc.function.arguments}

                await emit(
                    {"type": "tool_call", "name": tc.function.name, "args": args}
                )
                await emit(
                    {"type": "status", "message": f"Running {tc.function.name}…"}
                )

                raw_result = await call_tool(session, tc.function.name, args)
                preview = raw_result[:300].replace("\n", " ") or "(no text content)"
                await emit(
                    {
                        "type": "tool_result",
                        "name": tc.function.name,
                        "preview": preview,
                    }
                )

                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": raw_result,
                    }
                )
            continue

        reply = message.content or ""
        await emit({"type": "assistant_message", "text": reply})
        return
