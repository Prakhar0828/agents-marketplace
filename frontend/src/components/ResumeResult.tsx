import { Download, FileText } from "lucide-react";
import ReactMarkdown, { type Components } from "react-markdown";

interface Props {
  jobTitle: string;
  company: string;
  markdown: string;
  mdUrl: string;
  docxUrl: string;
  summary: string;
}

// Styled renderers for each markdown element — gives the resume output real
// typographic hierarchy without pulling in @tailwindcss/typography.
const mdComponents: Components = {
  h1: ({ children }) => (
    <h1 className="font-display text-2xl font-semibold tracking-tightish text-offwhite">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="mb-2 mt-6 text-xs font-semibold uppercase tracking-[0.25em] text-neon-cyan">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="mb-0.5 mt-4 text-[15px] font-semibold text-offwhite">
      {children}
    </h3>
  ),
  p: ({ children }) => (
    <p className="my-1.5 text-sm leading-relaxed text-offwhite/85">
      {children}
    </p>
  ),
  ul: ({ children }) => (
    <ul className="my-2 ml-5 list-disc space-y-1 text-sm text-offwhite/85 marker:text-neon-cyan/70">
      {children}
    </ul>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => (
    <strong className="font-semibold text-offwhite">{children}</strong>
  ),
  em: ({ children }) => <em className="text-muted">{children}</em>,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-neon-cyan underline-offset-2 hover:underline"
    >
      {children}
    </a>
  ),
  hr: () => <hr className="my-4 border-none" />,
};

export function ResumeResult({
  jobTitle,
  company,
  markdown,
  mdUrl,
  docxUrl,
  summary,
}: Props) {
  return (
    <div className="rounded-2xl border border-neon-cyan/20 bg-elevated/60 p-5 shadow-bloom-cyan backdrop-blur-sm">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-neon-cyan">
            <FileText className="h-3.5 w-3.5" />
            Optimized resume
          </div>
          <h3 className="mt-2 truncate font-display text-lg font-semibold">
            {jobTitle} · {company}
          </h3>
          {summary && <p className="mt-2 text-xs text-muted">{summary}</p>}
        </div>
        <div className="flex shrink-0 flex-col gap-2">
          <a href={docxUrl} download className="btn-ghost">
            <Download className="h-4 w-4" />
            .docx
          </a>
          <a href={mdUrl} download className="btn-ghost">
            <Download className="h-4 w-4" />
            .md
          </a>
        </div>
      </div>

      <div className="rounded-xl bg-base/80 p-6 shadow-inner ring-1 ring-white/5">
        <ReactMarkdown components={mdComponents}>{markdown}</ReactMarkdown>
      </div>
    </div>
  );
}
