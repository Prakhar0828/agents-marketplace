import { Crosshair, Download, ExternalLink } from "lucide-react";
import type { CompetitorRow } from "../lib/types";

interface Props {
  rows: CompetitorRow[];
  csvUrl: string | null;
}

export function CompetitorTable({ rows, csvUrl }: Props) {
  return (
    <div className="rounded-2xl border border-neon-amber/20 bg-elevated/60 p-5 shadow-bloom-amber backdrop-blur-sm">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-neon-amber">
            <Crosshair className="h-3.5 w-3.5" />
            Competitor Analysis
          </div>
          <h3 className="mt-2 font-display text-lg font-semibold">
            {rows.length} competitor{rows.length !== 1 ? "s" : ""} analysed
          </h3>
        </div>
        {csvUrl && (
          <a href={csvUrl} download className="btn-ghost shrink-0">
            <Download className="h-4 w-4" />
            CSV
          </a>
        )}
      </div>

      <div className="space-y-4">
        {rows.map((row) => (
          <div
            key={row.url}
            className="rounded-xl bg-base/80 p-4 shadow-inner ring-1 ring-white/5"
          >
            <div className="mb-3 flex items-center justify-between">
              <h4 className="font-display text-base font-semibold text-offwhite">
                {row.company}
              </h4>
              <a
                href={row.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs text-neon-amber hover:underline"
              >
                {row.url.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>

            <div className="grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <span className="text-[11px] uppercase tracking-wider text-muted">
                  Pricing
                </span>
                <p className="mt-0.5 text-offwhite/85">{row.pricing}</p>
              </div>
              <div>
                <span className="text-[11px] uppercase tracking-wider text-muted">
                  Key Features
                </span>
                <p className="mt-0.5 text-offwhite/85">{row.features}</p>
              </div>
              <div>
                <span className="text-[11px] uppercase tracking-wider text-muted">
                  Positioning
                </span>
                <p className="mt-0.5 text-offwhite/85">{row.positioning}</p>
              </div>
              <div>
                <span className="text-[11px] uppercase tracking-wider text-muted">
                  Tech Stack
                </span>
                <p className="mt-0.5 text-offwhite/85">{row.tech_stack}</p>
              </div>
              {row.notable && row.notable !== "—" && (
                <div className="sm:col-span-2">
                  <span className="text-[11px] uppercase tracking-wider text-muted">
                    Notable
                  </span>
                  <p className="mt-0.5 text-offwhite/85">{row.notable}</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
