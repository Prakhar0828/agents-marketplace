import type { AgentCard } from "./types";

const API_BASE = "/api";

export async function fetchAgents(): Promise<AgentCard[]> {
  const res = await fetch(`${API_BASE}/agents`);
  if (!res.ok) throw new Error(`Failed to load agents: ${res.status}`);
  return res.json();
}

export async function fetchAgent(id: string): Promise<AgentCard> {
  const res = await fetch(`${API_BASE}/agents/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(`Agent not found: ${id}`);
  return res.json();
}

export function downloadUrl(csvUrl: string): string {
  // csv_url from backend is already relative (/api/downloads/...)
  return csvUrl;
}

export interface ResumeUpload {
  id: string;
  filename: string;
  size: number;
}

export async function uploadResume(file: File): Promise<ResumeUpload> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/uploads/resume`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    let detail = `Upload failed (${res.status})`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Keep the default detail.
    }
    throw new Error(detail);
  }
  return res.json();
}
