import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Crosshair,
  FileText,
  Sparkles,
  Target,
  type LucideIcon,
} from "lucide-react";
import clsx from "clsx";
import type { AgentCard as AgentCardType } from "../lib/types";
import { ACCENTS } from "../lib/accent";

// Icon registry — backend sends icon names, we map to lucide components.
const ICONS: Record<string, LucideIcon> = {
  target: Target,
  sparkles: Sparkles,
  "file-text": FileText,
  crosshair: Crosshair,
};

interface Props {
  card: AgentCardType;
}

export function AgentCard({ card }: Props) {
  const accent = ACCENTS[card.accent];
  const Icon = ICONS[card.icon] ?? Sparkles;

  return (
    <Link
      to={`/hire/${card.id}`}
      className={clsx(
        "group relative flex flex-col rounded-3xl bg-card p-7 transition-all duration-300",
        "hover:bg-elevated",
        accent.glow
      )}
    >
      {/* Accent hairline at the top — pure tonal, no border */}
      <div
        className={clsx(
          "absolute left-7 right-7 top-0 h-px opacity-60",
          accent.bg
        )}
      />

      <div className="flex items-start justify-between">
        <div
          className={clsx(
            "flex h-12 w-12 items-center justify-center rounded-2xl",
            accent.bgSoft
          )}
        >
          <Icon className={clsx("h-6 w-6", accent.text)} />
        </div>
      </div>

      <h3 className="mt-6 font-display text-2xl font-semibold text-offwhite">
        {card.name}
      </h3>
      <p className="mt-1 text-sm text-muted">{card.tagline}</p>

      <p className="mt-5 text-sm leading-relaxed text-offwhite/80">
        {card.description}
      </p>

      <ul className="mt-5 flex flex-wrap gap-1.5">
        {card.capabilities.map((cap) => (
          <li
            key={cap}
            className="rounded-full bg-deepspace px-2.5 py-1 text-[11px] text-muted"
          >
            {cap}
          </li>
        ))}
      </ul>

      <div className="mt-7 flex items-center justify-between">
        <span className={clsx("text-xs uppercase tracking-wider", accent.text)}>
          Hire agent
        </span>
        <span
          className={clsx(
            "flex h-9 w-9 items-center justify-center rounded-full transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5",
            accent.bgSoft,
            accent.text
          )}
        >
          <ArrowUpRight className="h-4 w-4" />
        </span>
      </div>
    </Link>
  );
}
