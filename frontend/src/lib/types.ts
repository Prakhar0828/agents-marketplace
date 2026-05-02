// Mirror of backend/app/models.py Pydantic models. Keep in sync by hand.

export type AgentAccent = "emerald" | "violet" | "cyan" | "amber";
export type AgentMode = "intent_once" | "agentic_loop";

export interface AgentCard {
  id: string;
  name: string;
  tagline: string;
  description: string;
  accent: AgentAccent;
  icon: string;
  mode: AgentMode;
  capabilities: string[];
}

export interface Lead {
  name: string;
  platform: string;
  location: string;
  phone: string;
  website: string;
  instagram_handle: string;
  followers: number | null;
  rating: number | null;
  reviews: number | null;
  bio: string;
  score: number | null;
  score_reason: string;
}

export type ChatEvent =
  | { type: "user_message"; text: string }
  | { type: "assistant_message"; text: string }
  | { type: "status"; message: string }
  | { type: "tool_call"; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; name: string; preview: string }
  | {
      type: "intent";
      niche: string | null;
      location: string | null;
      count: number | null;
      hashtags: string[];
    }
  | {
      type: "leads_table";
      rows: Lead[];
      niche: string;
      location: string;
      csv_url: string | null;
    }
  | {
      type: "resume_result";
      job_title: string;
      company: string;
      markdown: string;
      md_url: string;
      docx_url: string;
      summary: string;
    }
  | {
      type: "competitor_result";
      rows: CompetitorRow[];
      csv_url: string | null;
    }
  | {
      type: "media_table";
      title: string;
      columns: string[];
      rows: string[][];
      csv_url: string | null;
    }
  | { type: "done" }
  | { type: "error"; message: string };

export interface CompetitorRow {
  company: string;
  url: string;
  pricing: string;
  features: string;
  positioning: string;
  tech_stack: string;
  notable: string;
}

// Transcript item types (reconstructed on the client from ChatEvents).
export type BubbleRole = "user" | "assistant";
export interface ChatBubble {
  id: string;
  role: BubbleRole;
  text: string;
}

export type TimelineItem =
  | { id: string; kind: "status"; message: string; ts: number }
  | {
      id: string;
      kind: "tool_call";
      name: string;
      args: Record<string, unknown>;
      ts: number;
    }
  | { id: string; kind: "tool_result"; name: string; preview: string; ts: number }
  | {
      id: string;
      kind: "intent";
      niche: string | null;
      location: string | null;
      count: number | null;
      hashtags: string[];
      ts: number;
    }
  | { id: string; kind: "error"; message: string; ts: number };
