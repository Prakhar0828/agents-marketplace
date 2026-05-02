import { useEffect, useState } from "react";
import { Cpu } from "lucide-react";
import type { AgentCard as AgentCardType } from "../lib/types";
import { fetchAgents } from "../lib/api";
import { AgentCard } from "../components/AgentCard";

export function Marketplace() {
  const [cards, setCards] = useState<AgentCardType[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAgents()
      .then(setCards)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load")
      );
  }, []);

  return (
    <div className="mx-auto max-w-6xl px-6 pb-24 pt-16">
      <header className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-neon-emerald/10 text-neon-emerald">
          <Cpu className="h-5 w-5" />
        </span>
        <span className="text-xs uppercase tracking-[0.3em] text-muted">
          Agent Marketplace
        </span>
      </header>

      <h1 className="mt-10 max-w-3xl font-display text-5xl font-semibold leading-tight">
        Hire a specialist agent.{" "}
        <span className="text-muted">Get real data back.</span>
      </h1>
      <p className="mt-5 max-w-2xl text-base leading-relaxed text-offwhite/80">
        Each agent is a purpose-built worker wired to live tools via Apify MCP
        and OpenAI. Pick one, describe what you need in plain English, and
        watch it stream results back in real time.
      </p>

      <section className="mt-16">
        {error && (
          <div className="rounded-xl bg-neon-red/10 px-4 py-3 text-sm text-neon-red">
            {error}
          </div>
        )}

        {cards === null && !error && (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            {[0, 1].map((i) => (
              <div
                key={i}
                className="h-72 animate-pulse rounded-3xl bg-card"
              />
            ))}
          </div>
        )}

        {cards && (
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            {cards.map((card) => (
              <AgentCard key={card.id} card={card} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
