import { Download, Instagram, MapPin, Star } from "lucide-react";
import clsx from "clsx";
import type { Lead } from "../lib/types";

interface Props {
  rows: Lead[];
  niche: string;
  location: string;
  csvUrl: string | null;
}

function platformColor(platform: string) {
  if (platform === "Google Maps") return "text-neon-emerald";
  if (platform === "Instagram") return "text-neon-violet";
  if (platform === "Both") return "text-offwhite";
  return "text-muted";
}

function scoreColor(score: number | null) {
  if (score == null) return "text-muted";
  if (score >= 7) return "text-neon-emerald";
  if (score >= 5) return "text-neon-amber";
  return "text-neon-red";
}

export function LeadsTable({ rows, niche, location, csvUrl }: Props) {
  return (
    <div className="mt-6 rounded-2xl bg-base p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="font-display text-lg font-semibold">
            {rows.length} leads · {niche} in {location}
          </h3>
          <p className="text-xs text-muted">
            Ranked by GPT across relevance, social proof, and completeness.
          </p>
        </div>
        {csvUrl && (
          <a
            href={csvUrl}
            download
            className="btn-ghost"
          >
            <Download className="h-4 w-4" />
            CSV
          </a>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wider text-muted">
              <th className="py-2 pr-3">#</th>
              <th className="py-2 pr-3">Business</th>
              <th className="py-2 pr-3">Source</th>
              <th className="py-2 pr-3">Handle</th>
              <th className="py-2 pr-3">Location</th>
              <th className="py-2 pr-3 text-right">Followers</th>
              <th className="py-2 pr-3 text-right">Rating</th>
              <th className="py-2 pr-3 text-right">Score</th>
              <th className="py-2 pr-3">Why</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((lead, i) => (
              <tr
                key={`${lead.name}-${i}`}
                className="border-t border-white/5 align-top"
              >
                <td className="py-3 pr-3 font-mono text-muted">{i + 1}</td>
                <td className="py-3 pr-3">
                  <div className="font-medium text-offwhite">{lead.name}</div>
                  {lead.website !== "—" && (
                    <a
                      href={
                        lead.website.startsWith("http")
                          ? lead.website
                          : `https://${lead.website}`
                      }
                      target="_blank"
                      rel="noreferrer"
                      className="text-[11px] text-muted hover:text-neon-emerald"
                    >
                      {lead.website}
                    </a>
                  )}
                </td>
                <td className={clsx("py-3 pr-3", platformColor(lead.platform))}>
                  {lead.platform}
                </td>
                <td className="py-3 pr-3 text-muted">
                  {lead.instagram_handle !== "—" ? (
                    <span className="inline-flex items-center gap-1">
                      <Instagram className="h-3 w-3" />
                      {lead.instagram_handle}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="py-3 pr-3 text-offwhite/80">
                  <span className="inline-flex items-center gap-1">
                    <MapPin className="h-3 w-3 text-muted" />
                    {lead.location.slice(0, 24)}
                  </span>
                </td>
                <td className="py-3 pr-3 text-right tabular-nums text-offwhite/80">
                  {lead.followers != null
                    ? lead.followers.toLocaleString()
                    : "—"}
                </td>
                <td className="py-3 pr-3 text-right text-offwhite/80">
                  {lead.rating != null ? (
                    <span className="inline-flex items-center gap-1">
                      {lead.rating}
                      <Star className="h-3 w-3 text-neon-amber" />
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
                <td
                  className={clsx(
                    "py-3 pr-3 text-right font-semibold tabular-nums",
                    scoreColor(lead.score)
                  )}
                >
                  {lead.score ?? "—"}
                </td>
                <td className="py-3 pr-3 text-xs text-muted max-w-[240px]">
                  {lead.score_reason}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
