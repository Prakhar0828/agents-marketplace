"""GET /api/agents — list the marketplace cards."""

from fastapi import APIRouter, HTTPException

from ..models import AgentCard
from ..registry import get_entry, list_cards

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=list[AgentCard])
async def list_agents() -> list[AgentCard]:
    return list_cards()


@router.get("/{agent_id}", response_model=AgentCard)
async def get_agent(agent_id: str) -> AgentCard:
    entry = get_entry(agent_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    return entry.card
