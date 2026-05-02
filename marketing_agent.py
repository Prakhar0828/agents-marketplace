"""
Marketing Agent
Creates UGC and cinematic ads via the Higgsfield MCP server.
GPT-5.4 acts as creative director — extracts the brief and writes generation prompts.

UGC workflow:      generate_image (soul_2) → generate_video (seedance_2_0)
Cinematic workflow: generate_video (kling3_0)
"""

import asyncio
import base64
import json
import os
import sys
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
HIGGSFIELD_API_KEY = os.getenv("HIGGSFIELD_API_KEY")
HIGGSFIELD_MCP_URL = os.getenv("HIGGSFIELD_MCP_URL", "https://mcp.higgsfield.ai/mcp")
MODEL = "gpt-5.4"

# Higgsfield model IDs
UGC_IMAGE_MODEL = "soul_2"          # realistic person/character image
UGC_VIDEO_MODEL = "seedance_2_0"    # reference-driven animation (image → video)
CINEMATIC_MODEL = "kling3_0"        # multi-shot cinematic video

console = Console()

# ── Lenient MCP session ───────────────────────────────────────────────────────

class LenientClientSession(ClientSession):
    """Skip strict output-schema validation in case Higgsfield uses non-standard types."""
    async def _validate_tool_result(self, name: str, result: Any) -> None:
        pass

# ── Helpers ───────────────────────────────────────────────────────────────────

def validate_env() -> None:
    missing = [k for k, v in [
        ("OPENAI_API_KEY",     OPENAI_API_KEY),
        ("HIGGSFIELD_API_KEY", HIGGSFIELD_API_KEY),
        ("HIGGSFIELD_MCP_URL", HIGGSFIELD_MCP_URL),
    ] if not v]
    if missing:
        console.print(f"[bold red]Missing env vars:[/bold red] {', '.join(missing)}")
        sys.exit(1)


async def call_tool(session: LenientClientSession, name: str, inputs: dict) -> str:
    result = await session.call_tool(name, inputs)
    parts = [item.text for item in result.content if hasattr(item, "text")]
    return "\n".join(parts) if parts else ""


def extract_job_id(raw: str) -> str | None:
    """Pull the job/generation ID out of a Higgsfield tool response."""
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data.get("id") or data.get("job_id") or data.get("generation_id")
    except (json.JSONDecodeError, TypeError):
        pass
    return None


# ── Brief extraction ──────────────────────────────────────────────────────────

def extract_brief(client: OpenAI, user_message: str) -> dict:
    """Parse a free-form request into a structured creative brief."""
    resp = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a creative director at a marketing agency.\n"
                    "Extract a structured ad brief from the user's message.\n\n"
                    "Return JSON with these keys:\n"
                    "  ad_type      (str)  — 'ugc' or 'cinematic'\n"
                    "                        ugc = authentic, person-to-camera, social-native\n"
                    "                        cinematic = high-production, brand-film style\n"
                    "  product      (str)  — what is being advertised\n"
                    "  audience     (str)  — target audience description\n"
                    "  tone         (str)  — e.g. energetic, luxurious, casual, inspirational, playful\n"
                    "  key_message  (str)  — the core message or CTA\n"
                    "  aspect_ratio (str)  — '9:16' for vertical/social (default), '16:9' for widescreen\n\n"
                    "If the user doesn't specify ad_type, infer it:\n"
                    "  - Mentions 'UGC', 'creator', 'authentic', 'TikTok', 'Reels' → ugc\n"
                    "  - Mentions 'cinematic', 'brand film', 'luxury', 'widescreen' → cinematic"
                ),
            },
            {"role": "user", "content": user_message},
        ],
    )
    return json.loads(resp.choices[0].message.content)


# ── Prompt crafting ───────────────────────────────────────────────────────────

def craft_ugc_prompts(client: OpenAI, brief: dict) -> tuple[str, str]:
    """
    Write two prompts for the UGC pipeline:
      1. character_prompt  → who appears in the ad (for soul_2 image generation)
      2. motion_prompt     → what they do in the video (for seedance_2_0 animation)
    """
    resp = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a UGC ad creative director.\n\n"
                    "Write two prompts for a two-step AI generation pipeline.\n\n"
                    "Return JSON with:\n"
                    "  character_prompt (str)\n"
                    "    — Describe the UGC creator in detail: age, ethnicity, style, expression, "
                    "clothing, background setting. Make them feel real and relatable to the target audience. "
                    "Shot on iPhone, natural lighting, slightly candid feel. "
                    "Do NOT mention the product here — focus only on the person.\n\n"
                    "  motion_prompt (str)\n"
                    "    — Describe what the person does in the video. They should naturally "
                    "interact with or mention the product. Keep it authentic: talking to camera, "
                    "holding up the product, showing a reaction, gesturing enthusiastically. "
                    "Match the tone of the brief. 1-2 sentences."
                ),
            },
            {"role": "user", "content": json.dumps(brief)},
        ],
    )
    data = json.loads(resp.choices[0].message.content)
    return data.get("character_prompt", ""), data.get("motion_prompt", "")


def craft_cinematic_prompt(client: OpenAI, brief: dict) -> str:
    """Write a single rich cinematic scene prompt for kling3_0."""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a cinematic ad director writing a shot description for an AI video model.\n\n"
                    "Write a single, dense prompt (3-5 sentences) that describes:\n"
                    "  • The scene and how the product is featured\n"
                    "  • Camera movement (e.g. slow push-in, aerial descent, tracking shot, dolly zoom)\n"
                    "  • Lighting and color grade (e.g. golden hour, cool cinematic teal, high contrast)\n"
                    "  • Mood and atmosphere\n\n"
                    "Write as a director's brief — specific, visual, evocative. "
                    "Match the tone and audience from the brief exactly."
                ),
            },
            {"role": "user", "content": json.dumps(brief)},
        ],
    )
    return resp.choices[0].message.content.strip()


# ── Workflows ─────────────────────────────────────────────────────────────────

async def run_ugc_workflow(
    session: LenientClientSession,
    client: OpenAI,
    brief: dict,
) -> None:
    console.print("\n[bold magenta]── UGC Ad Workflow ──[/bold magenta]")

    # Craft prompts
    with console.status("[dim]GPT-5.4 writing UGC prompts…[/dim]", spinner="dots"):
        character_prompt, motion_prompt = craft_ugc_prompts(client, brief)

    console.print(Panel(
        f"[bold]Character prompt[/bold]\n{character_prompt}\n\n"
        f"[bold]Motion prompt[/bold]\n{motion_prompt}",
        title="[magenta]Creative Prompts[/magenta]",
        border_style="magenta",
    ))

    # Step 1 — Character image
    console.print("\n  [dim]Step 1/2[/dim] — Generating character image [dim](soul_2)[/dim]")
    with console.status("[dim]Submitting image job to Higgsfield…[/dim]", spinner="dots"):
        raw_image = await call_tool(session, "generate_image", {
            "params": {
                "model":        UGC_IMAGE_MODEL,
                "prompt":       character_prompt,
                "aspect_ratio": brief.get("aspect_ratio", "9:16"),
            }
        })

    image_job_id = extract_job_id(raw_image)
    console.print(
        f"  [green]✓[/green] Image job submitted"
        + (f" · ID: [bold]{image_job_id}[/bold]" if image_job_id else "")
    )

    # Step 2 — Animate to video
    console.print("\n  [dim]Step 2/2[/dim] — Animating to video [dim](seedance_2_0)[/dim]")

    video_params: dict[str, Any] = {
        "model":        UGC_VIDEO_MODEL,
        "prompt":       motion_prompt,
        "aspect_ratio": brief.get("aspect_ratio", "9:16"),
    }
    if image_job_id:
        video_params["medias"] = [{"value": image_job_id, "role": "start_image"}]

    with console.status("[dim]Submitting video job to Higgsfield…[/dim]", spinner="dots"):
        raw_video = await call_tool(session, "generate_video", {"params": video_params})

    video_job_id = extract_job_id(raw_video)
    console.print(
        f"  [green]✓[/green] Video job submitted"
        + (f" · ID: [bold]{video_job_id}[/bold]" if video_job_id else "")
    )

    console.print(Panel(
        f"[dim]Product[/dim]      {brief.get('product', '—')}\n"
        f"[dim]Audience[/dim]     {brief.get('audience', '—')}\n"
        f"[dim]Tone[/dim]         {brief.get('tone', '—')}\n"
        f"[dim]Key message[/dim]  {brief.get('key_message', '—')}\n\n"
        f"[dim]Image job[/dim]    [bold]{image_job_id or 'submitted'}[/bold]\n"
        f"[dim]Video job[/dim]    [bold]{video_job_id or 'submitted'}[/bold]",
        title="[green]✓  UGC Ad Submitted[/green]",
        border_style="green",
    ))


async def run_cinematic_workflow(
    session: LenientClientSession,
    client: OpenAI,
    brief: dict,
) -> None:
    console.print("\n[bold cyan]── Cinematic Ad Workflow ──[/bold cyan]")

    # Craft prompt
    with console.status("[dim]GPT-5.4 writing cinematic prompt…[/dim]", spinner="dots"):
        prompt = craft_cinematic_prompt(client, brief)

    console.print(Panel(
        prompt,
        title="[cyan]Cinematic Prompt[/cyan]",
        border_style="cyan",
    ))

    # Generate video
    console.print("\n  [dim]Generating cinematic video [dim](kling3_0)[/dim]")
    with console.status("[dim]Submitting video job to Higgsfield…[/dim]", spinner="dots"):
        raw_video = await call_tool(session, "generate_video", {
            "params": {
                "model":        CINEMATIC_MODEL,
                "prompt":       prompt,
                "aspect_ratio": brief.get("aspect_ratio", "16:9"),
            }
        })

    video_job_id = extract_job_id(raw_video)
    console.print(
        f"  [green]✓[/green] Video job submitted"
        + (f" · ID: [bold]{video_job_id}[/bold]" if video_job_id else "")
    )

    console.print(Panel(
        f"[dim]Product[/dim]      {brief.get('product', '—')}\n"
        f"[dim]Audience[/dim]     {brief.get('audience', '—')}\n"
        f"[dim]Tone[/dim]         {brief.get('tone', '—')}\n"
        f"[dim]Key message[/dim]  {brief.get('key_message', '—')}\n\n"
        f"[dim]Video job[/dim]    [bold]{video_job_id or 'submitted'}[/bold]",
        title="[green]✓  Cinematic Ad Submitted[/green]",
        border_style="green",
    ))


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    validate_env()

    console.print(Panel.fit(
        "[bold cyan]Marketing Agent[/bold cyan]\n"
        "[dim]UGC & Cinematic Ads · Higgsfield MCP + GPT-5.4[/dim]",
        border_style="cyan",
    ))

    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    encoded = base64.b64encode(HIGGSFIELD_API_KEY.encode()).decode()
    headers = {"Authorization": f"Basic {encoded}"}

    try:
        async with streamablehttp_client(HIGGSFIELD_MCP_URL, headers=headers) as (read, write, _):
            async with LenientClientSession(read, write) as session:
                await session.initialize()

                with console.status("Fetching tools…", spinner="dots"):
                    raw_tools = (await session.list_tools()).tools

                console.print(
                    f"[green]✓[/green] Connected — [bold]{len(raw_tools)}[/bold] Higgsfield tools loaded\n"
                )

                console.print(Rule("[dim]Describe the ad you want · type [bold]quit[/bold] to exit[/dim]"))
                console.print("[dim]Examples:[/dim]")
                console.print("[dim]  'UGC ad for my matcha powder, targeting health-conscious millennials'[/dim]")
                console.print("[dim]  'Cinematic ad for a luxury watch brand, widescreen, golden hour'[/dim]\n")

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

                    # Extract brief
                    with console.status("Understanding your request…", spinner="dots"):
                        brief = extract_brief(openai_client, user_input)

                    console.print(
                        f"\n  [dim]Type:[/dim] [bold]{brief.get('ad_type', '?').upper()}[/bold]  "
                        f"[dim]Product:[/dim] {brief.get('product', '?')}  "
                        f"[dim]Tone:[/dim] {brief.get('tone', '?')}  "
                        f"[dim]Ratio:[/dim] {brief.get('aspect_ratio', '9:16')}\n"
                    )

                    ad_type = brief.get("ad_type", "ugc").lower()

                    if ad_type == "cinematic":
                        await run_cinematic_workflow(session, openai_client, brief)
                    else:
                        await run_ugc_workflow(session, openai_client, brief)

    except Exception as exc:
        console.print(f"\n[bold red]Fatal error:[/bold red] {exc}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
