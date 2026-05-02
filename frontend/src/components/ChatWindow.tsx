import { useEffect, useRef, useState } from "react";
import { ArrowRight, FileText, Paperclip, X } from "lucide-react";
import clsx from "clsx";
import type { AgentAccent, ChatBubble } from "../lib/types";
import { ACCENTS } from "../lib/accent";
import { uploadResume } from "../lib/api";
import { MessageBubble } from "./MessageBubble";
import { ResumeResult } from "./ResumeResult";

interface ResumePayload {
  jobTitle: string;
  company: string;
  markdown: string;
  mdUrl: string;
  docxUrl: string;
  summary: string;
}

interface Attachment {
  id: string;
  filename: string;
  size: number;
}

interface Props {
  bubbles: ChatBubble[];
  accent: AgentAccent;
  thinking: boolean;
  disabled: boolean;
  // When true, show the paperclip + allow attaching a resume PDF. Used only
  // for the resume-optimizer agent to keep the other chat UIs minimal.
  allowResumeUpload?: boolean;
  // When set, renders the optimized resume inline at the bottom of the
  // transcript so the user sees the output right where they're reading.
  resume?: ResumePayload | null;
  onSend: (text: string, resumeFileId?: string) => void;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ChatWindow({
  bubbles,
  accent,
  thinking,
  disabled,
  allowResumeUpload,
  resume,
  onSend,
}: Props) {
  const [draft, setDraft] = useState("");
  const [attachment, setAttachment] = useState<Attachment | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const a = ACCENTS[accent];
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [bubbles.length, thinking, resume?.markdown]);

  async function onPickFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    // Reset the input so the same file can be re-picked after removal.
    e.target.value = "";
    if (!file) return;

    setUploadError(null);
    setUploading(true);
    try {
      const res = await uploadResume(file);
      setAttachment({
        id: res.id,
        filename: res.filename,
        size: res.size,
      });
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  function submit(e?: React.FormEvent) {
    e?.preventDefault();
    const text = draft.trim();
    // A bare attachment (no text) is still sendable — the agent prompts the
    // user in chat for title/company on the next turn.
    if ((!text && !attachment) || disabled) return;
    onSend(text, attachment?.id);
    setDraft("");
    // Keep the attachment "consumed" for the current turn but clear it so the
    // user isn't tempted to re-send the same file. The backend has stashed
    // the parsed text in state on the server side.
    setAttachment(null);
  }

  const canSubmit =
    !disabled && !uploading && (draft.trim().length > 0 || attachment !== null);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div
        ref={scrollRef}
        className="flex-1 space-y-4 overflow-y-auto px-6 py-8 no-scrollbar"
      >
        {bubbles.map((b) => (
          <MessageBubble key={b.id} bubble={b} accent={accent} />
        ))}
        {resume && (
          <ResumeResult
            jobTitle={resume.jobTitle}
            company={resume.company}
            markdown={resume.markdown}
            mdUrl={resume.mdUrl}
            docxUrl={resume.docxUrl}
            summary={resume.summary}
          />
        )}
        {thinking && (
          <div className="flex items-center gap-2 px-1 text-xs text-muted">
            <span className={clsx("status-dot", a.bg)} />
            Agent is working…
          </div>
        )}
      </div>

      <form onSubmit={submit} className="flex flex-col gap-2 bg-base px-6 py-4">
        {/* Attachment chip + errors */}
        {(attachment || uploadError || uploading) && (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {uploading && (
              <span className="inline-flex items-center gap-2 rounded-full bg-deepspace px-3 py-1.5 text-muted">
                <span className={clsx("status-dot", a.bg)} />
                Uploading…
              </span>
            )}
            {attachment && (
              <span
                className={clsx(
                  "inline-flex items-center gap-2 rounded-full bg-deepspace px-3 py-1.5",
                  a.text
                )}
              >
                <FileText className="h-3.5 w-3.5" />
                <span className="text-offwhite/90">{attachment.filename}</span>
                <span className="text-muted">
                  {formatSize(attachment.size)}
                </span>
                <button
                  type="button"
                  onClick={() => setAttachment(null)}
                  className="ml-1 rounded-full p-0.5 text-muted hover:text-offwhite"
                  aria-label="Remove attachment"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            )}
            {uploadError && (
              <span className="inline-flex items-center gap-2 rounded-full bg-neon-red/10 px-3 py-1.5 text-neon-red">
                {uploadError}
                <button
                  type="button"
                  onClick={() => setUploadError(null)}
                  className="ml-1 rounded-full p-0.5 hover:bg-neon-red/15"
                  aria-label="Dismiss error"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            )}
          </div>
        )}

        <div className="flex items-center gap-3">
          {allowResumeUpload && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={onPickFile}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={disabled || uploading}
                className={clsx(
                  "flex h-11 w-11 shrink-0 items-center justify-center rounded-full transition-all duration-200 disabled:opacity-40",
                  a.bgSoft,
                  a.text,
                  "hover:bg-elevated"
                )}
                aria-label="Attach resume PDF"
                title="Attach resume PDF"
              >
                <Paperclip className="h-4 w-4" />
              </button>
            </>
          )}

          <input
            className="input-bare rounded-xl"
            placeholder={
              disabled
                ? "Connecting…"
                : allowResumeUpload && !attachment
                  ? "Attach your resume, then describe the target role…"
                  : "Describe what you need, or reply to the agent…"
            }
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            disabled={disabled}
          />
          <button
            type="submit"
            disabled={!canSubmit}
            className={clsx(
              "flex h-11 w-11 shrink-0 items-center justify-center rounded-full transition-all duration-200 disabled:opacity-40",
              a.gradient,
              canSubmit ? a.glow : ""
            )}
          >
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
