import type { AgentAccent } from "./types";

// Tailwind can't compose class names dynamically — we need the full class
// strings to appear verbatim somewhere so the JIT picks them up. This
// dictionary is the single source of truth for per-accent styling.
export interface AccentClasses {
  text: string;
  bg: string;
  bgSoft: string;
  ring: string;
  glow: string;
  gradient: string;
  cta: string;
  timelineDot: string;
}

export const ACCENTS: Record<AgentAccent, AccentClasses> = {
  emerald: {
    text: "text-neon-emerald",
    bg: "bg-neon-emerald",
    bgSoft: "bg-neon-emerald/10",
    ring: "ring-neon-emerald/30",
    glow: "shadow-bloom-emerald hover:shadow-glow-emerald",
    gradient:
      "bg-[linear-gradient(135deg,#3EFF9E_0%,#14B867_100%)] text-deepspace",
    cta: "btn-primary",
    timelineDot: "bg-neon-emerald",
  },
  violet: {
    text: "text-neon-violet",
    bg: "bg-neon-violet",
    bgSoft: "bg-neon-violet/10",
    ring: "ring-neon-violet/30",
    glow: "shadow-bloom-violet hover:shadow-glow-violet",
    gradient:
      "bg-[linear-gradient(135deg,#B07CFF_0%,#7A3BFF_100%)] text-deepspace",
    cta: "btn-primary btn-primary-violet",
    timelineDot: "bg-neon-violet",
  },
  cyan: {
    text: "text-neon-cyan",
    bg: "bg-neon-cyan",
    bgSoft: "bg-neon-cyan/10",
    ring: "ring-neon-cyan/30",
    glow: "shadow-bloom-cyan hover:shadow-glow-cyan",
    gradient:
      "bg-[linear-gradient(135deg,#5EE1FF_0%,#1BA6D4_100%)] text-deepspace",
    cta: "btn-primary btn-primary-cyan",
    timelineDot: "bg-neon-cyan",
  },
  amber: {
    text: "text-neon-amber",
    bg: "bg-neon-amber",
    bgSoft: "bg-neon-amber/10",
    ring: "ring-neon-amber/30",
    glow: "shadow-bloom-amber hover:shadow-glow-amber",
    gradient:
      "bg-[linear-gradient(135deg,#FFD45E_0%,#D4A01B_100%)] text-deepspace",
    cta: "btn-primary btn-primary-amber",
    timelineDot: "bg-neon-amber",
  },
};
