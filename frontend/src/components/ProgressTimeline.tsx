import {
  AlertTriangle,
  Cog,
  MapPin,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import clsx from "clsx";
import type { AgentAccent, TimelineItem } from "../lib/types";
import { ACCENTS } from "../lib/accent";

interface Props {
  items: TimelineItem[];
  accent: AgentAccent;
}

function iconFor(kind: TimelineItem["kind"]): LucideIcon {
  switch (kind) {
    case "tool_call":
    case "tool_result":
      return Cog;
    case "intent":
      return MapPin;
    case "error":
      return AlertTriangle;
    default:
      return Sparkles;
  }
}

function label(item: TimelineItem): string {
  switch (item.kind) {
    case "status":
      return item.message;
    case "tool_call":
      return `Calling ${item.name}`;
    case "tool_result":
      return `${item.name} → ${item.preview}`;
    case "intent":
      return `Intent locked: ${item.niche ?? "?"} in ${item.location ?? "?"} (x${item.count ?? "?"})`;
    case "error":
      return item.message;
  }
}

export function ProgressTimeline({ items, accent }: Props) {
  const a = ACCENTS[accent];

  if (items.length === 0) {
    return (
      <div className="px-1 py-4 text-sm text-muted">
        Progress events will appear here as the agent works.
      </div>
    );
  }

  return (
    <ol className="relative space-y-5 px-1 py-4">
      {/* Timeline spine — a dotted ghost line */}
      <div
        aria-hidden
        className="absolute left-[9px] top-2 bottom-2 w-px opacity-30"
        style={{
          backgroundImage:
            "linear-gradient(to bottom, rgba(239,255,227,0.6) 50%, transparent 50%)",
          backgroundSize: "1px 6px",
        }}
      />
      {items.map((item) => {
        const Icon = iconFor(item.kind);
        const isError = item.kind === "error";
        return (
          <li key={item.id} className="relative pl-8">
            <span
              className={clsx(
                "absolute left-0 top-0.5 flex h-[18px] w-[18px] items-center justify-center rounded-full",
                isError ? "bg-neon-red/15 text-neon-red" : clsx(a.bgSoft, a.text)
              )}
            >
              <Icon className="h-3 w-3" />
            </span>
            <div
              className={clsx(
                "text-sm leading-snug",
                isError ? "text-neon-red" : "text-offwhite/90"
              )}
            >
              {label(item)}
            </div>
            {item.kind === "tool_call" && (
              <pre className="mt-1 overflow-x-auto rounded-lg bg-deepspace px-3 py-2 text-[11px] text-muted">
                {JSON.stringify(item.args, null, 2)}
              </pre>
            )}
          </li>
        );
      })}
    </ol>
  );
}
