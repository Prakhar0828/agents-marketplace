import clsx from "clsx";
import ReactMarkdown from "react-markdown";
import type { AgentAccent, ChatBubble } from "../lib/types";
import { ACCENTS } from "../lib/accent";

interface Props {
  bubble: ChatBubble;
  accent: AgentAccent;
}

export function MessageBubble({ bubble, accent }: Props) {
  const a = ACCENTS[accent];
  const isUser = bubble.role === "user";

  return (
    <div
      className={clsx(
        "flex w-full",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={clsx(
          "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-elevated text-offwhite"
            : clsx("bg-card text-offwhite/90", a.ring, "ring-1")
        )}
      >
        <div className="prose prose-invert prose-sm max-w-none prose-p:my-1.5 prose-strong:text-offwhite prose-code:text-neon-emerald">
          <ReactMarkdown>{bubble.text}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
