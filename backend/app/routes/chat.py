"""WebSocket /ws/chat/{agent_id} — one long-lived chat session per connection."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from openai import OpenAI
from starlette.websockets import WebSocketState

from ..config import OPENAI_API_KEY
from ..mcp_client import apify_session
from ..registry import get_entry

log = logging.getLogger("agent_marketplace.chat")

router = APIRouter(tags=["chat"])


@router.websocket("/ws/chat/{agent_id}")
async def chat_ws(websocket: WebSocket, agent_id: str) -> None:
    await websocket.accept()

    entry = get_entry(agent_id)
    if entry is None:
        await websocket.send_json(
            {"type": "error", "message": f"Unknown agent: {agent_id}"}
        )
        await websocket.close()
        return

    async def emit(event: dict) -> None:
        if websocket.application_state != WebSocketState.CONNECTED:
            return
        try:
            await websocket.send_json(event)
        except (WebSocketDisconnect, RuntimeError):
            # Client vanished between the state check and the send — not fatal.
            pass

    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    state = entry.new_state()

    try:
        # Send greeting before opening the (potentially slow) MCP session so the
        # user sees something immediately.
        await emit({"type": "assistant_message", "text": entry.greeting})
        await emit({"type": "status", "message": "Connecting to Apify…"})

        async with apify_session(entry.actors) as session:
            await emit({"type": "status", "message": "Ready."})

            while True:
                try:
                    data = await websocket.receive_json()
                except (WebSocketDisconnect, RuntimeError):
                    # Client went away — either clean close or the socket was
                    # already torn down. Nothing to recover.
                    break

                user_text = (data or {}).get("text", "").strip()
                # Any extra fields on the incoming message (e.g. resume_file_id)
                # are forwarded as keyword args so agent-specific payloads don't
                # pollute the shared handler signature.
                extra = {
                    k: v
                    for k, v in (data or {}).items()
                    if k != "text" and v is not None
                }
                if not user_text and not extra:
                    continue

                if user_text:
                    await emit({"type": "user_message", "text": user_text})

                try:
                    await entry.handler(
                        user_text, session, openai_client, state, emit, **extra
                    )
                except Exception as exc:  # noqa: BLE001 — surface all agent errors
                    log.exception("Agent handler crashed")
                    await emit(
                        {
                            "type": "error",
                            "message": f"The agent hit an error: {exc}",
                        }
                    )
                finally:
                    await emit({"type": "done"})

    except WebSocketDisconnect:
        pass
    except BaseException as exc:  # noqa: BLE001 — also catches ExceptionGroup
        # When the client disconnects mid-MCP-handshake, the anyio TaskGroup
        # re-raises the WebSocketDisconnect/RuntimeError wrapped in an
        # ExceptionGroup. Treat any group that only contains disconnect-ish
        # errors as a clean client bye.
        if _is_client_disconnect(exc):
            log.debug("Client disconnected during session startup")
        else:
            log.exception("Chat session crashed")
            try:
                await emit({"type": "error", "message": str(exc)})
            except Exception:
                pass
    finally:
        # The ASGI layer sometimes sends its own close frame first (e.g. after
        # a server-side exception), which makes a second close() raise. We
        # swallow that because the socket is definitely gone either way.
        if websocket.application_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
            except RuntimeError:
                pass


def _is_client_disconnect(exc: BaseException) -> bool:
    """Walk an exception (optionally an ExceptionGroup) and return True when
    every leaf is a WebSocketDisconnect or the 'not connected' RuntimeError
    that starlette raises after the socket has been torn down."""

    def is_disconnect_leaf(e: BaseException) -> bool:
        if isinstance(e, WebSocketDisconnect):
            return True
        if isinstance(e, RuntimeError) and "not connected" in str(e).lower():
            return True
        return False

    if isinstance(exc, BaseExceptionGroup):
        return all(_is_client_disconnect(e) for e in exc.exceptions)
    return is_disconnect_leaf(exc)
