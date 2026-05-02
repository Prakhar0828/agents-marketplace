import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Radio } from "lucide-react";
import clsx from "clsx";
import type {
  AgentCard,
  ChatBubble,
  ChatEvent,
  Lead,
  TimelineItem,
} from "../lib/types";
import { fetchAgent } from "../lib/api";
import { useAgentSocket } from "../lib/useAgentSocket";
import { ACCENTS } from "../lib/accent";
import { ChatWindow } from "../components/ChatWindow";
import { ProgressTimeline } from "../components/ProgressTimeline";
import { LeadsTable } from "../components/LeadsTable";

interface LeadsPayload {
  rows: Lead[];
  niche: string;
  location: string;
  csvUrl: string | null;
}

interface ResumePayload {
  jobTitle: string;
  company: string;
  markdown: string;
  mdUrl: string;
  docxUrl: string;
  summary: string;
}

function reduceEvents(events: ChatEvent[]): {
  bubbles: ChatBubble[];
  timeline: TimelineItem[];
  leads: LeadsPayload | null;
  resume: ResumePayload | null;
} {
  const bubbles: ChatBubble[] = [];
  const timeline: TimelineItem[] = [];
  let leads: LeadsPayload | null = null;
  let resume: ResumePayload | null = null;

  events.forEach((evt, idx) => {
    const id = `e${idx}`;
    const ts = idx;
    switch (evt.type) {
      case "user_message":
        bubbles.push({ id, role: "user", text: evt.text });
        break;
      case "assistant_message":
        bubbles.push({ id, role: "assistant", text: evt.text });
        break;
      case "status":
        timeline.push({ id, kind: "status", message: evt.message, ts });
        break;
      case "tool_call":
        timeline.push({
          id,
          kind: "tool_call",
          name: evt.name,
          args: evt.args,
          ts,
        });
        break;
      case "tool_result":
        timeline.push({
          id,
          kind: "tool_result",
          name: evt.name,
          preview: evt.preview,
          ts,
        });
        break;
      case "intent":
        timeline.push({
          id,
          kind: "intent",
          niche: evt.niche,
          location: evt.location,
          count: evt.count,
          hashtags: evt.hashtags,
          ts,
        });
        break;
      case "leads_table":
        leads = {
          rows: evt.rows,
          niche: evt.niche,
          location: evt.location,
          csvUrl: evt.csv_url,
        };
        break;
      case "resume_result":
        resume = {
          jobTitle: evt.job_title,
          company: evt.company,
          markdown: evt.markdown,
          mdUrl: evt.md_url,
          docxUrl: evt.docx_url,
          summary: evt.summary,
        };
        break;
      case "error":
        timeline.push({ id, kind: "error", message: evt.message, ts });
        break;
      case "done":
        break;
    }
  });

  return { bubbles, timeline, leads, resume };
}

export function ChatRoom() {
  const { agentId = "" } = useParams();
  const [card, setCard] = useState<AgentCard | null>(null);
  const [cardError, setCardError] = useState<string | null>(null);

  useEffect(() => {
    fetchAgent(agentId)
      .then(setCard)
      .catch((e: unknown) =>
        setCardError(e instanceof Error ? e.message : "Failed to load")
      );
  }, [agentId]);

  const { events, send, thinking, status } = useAgentSocket(agentId);

  const { bubbles, timeline, leads, resume } = useMemo(
    () => reduceEvents(events),
    [events]
  );

  if (cardError) {
    return (
      <div className="mx-auto max-w-xl p-10">
        <div className="rounded-xl bg-neon-red/10 px-4 py-3 text-sm text-neon-red">
          {cardError}
        </div>
        <Link to="/" className="btn-ghost mt-6">
          <ArrowLeft className="h-4 w-4" /> Back to marketplace
        </Link>
      </div>
    );
  }

  if (!card) {
    return <div className="p-10 text-muted">Loading agent…</div>;
  }

  const a = ACCENTS[card.accent];
  const connected = status === "open";
  const statusLabel = {
    connecting: "Connecting…",
    open: "Live",
    closed: "Disconnected",
    error: "Error",
  }[status];

  return (
    <div className="flex h-screen flex-col bg-base">
      <header className="flex items-center justify-between bg-deepspace px-6 py-4">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="flex h-9 w-9 items-center justify-center rounded-full text-muted transition-colors hover:text-offwhite"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="font-display text-base font-semibold">
              {card.name}
            </div>
            <div className="text-xs text-muted">{card.tagline}</div>
          </div>
        </div>
        <div
          className={clsx(
            "flex items-center gap-2 rounded-full px-3 py-1.5 text-xs",
            connected ? a.bgSoft : "bg-neon-red/10",
            connected ? a.text : "text-neon-red"
          )}
        >
          <Radio className="h-3 w-3" />
          {statusLabel}
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* Chat column */}
        <div className="flex min-h-0 flex-1 flex-col bg-base">
          <ChatWindow
            bubbles={bubbles}
            accent={card.accent}
            thinking={thinking}
            disabled={!connected}
            allowResumeUpload={card.id === "resume-optimizer"}
            resume={resume}
            onSend={(text, resumeFileId) =>
              send(text, resumeFileId ? { resume_file_id: resumeFileId } : undefined)
            }
          />
        </div>

        {/* Progress + results column */}
        <aside className="hidden min-h-0 w-[420px] shrink-0 flex-col overflow-y-auto bg-deepspace px-5 py-6 no-scrollbar lg:flex">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs uppercase tracking-[0.25em] text-muted">
              Run timeline
            </span>
            <span className={clsx("text-[10px] uppercase", a.text)}>
              {card.mode === "intent_once" ? "One-shot" : "Agentic loop"}
            </span>
          </div>
          <ProgressTimeline items={timeline} accent={card.accent} />
          {leads && (
            <LeadsTable
              rows={leads.rows}
              niche={leads.niche}
              location={leads.location}
              csvUrl={leads.csvUrl}
            />
          )}
        </aside>
      </div>
    </div>
  );
}
