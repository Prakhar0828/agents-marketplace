import type { Config } from "tailwindcss";

// Depth-mode dark palette from the ui-design skill. Level 0–3 surfaces are
// tonal shifts, never 1px borders. Neon accents are per-agent: emerald for
// Sales Lead, violet for Content Research.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        deepspace: "#0E0E0E",
        base: "#131313",
        card: "#1F1F1F",
        elevated: "#2A2A2A",
        offwhite: "#EFFFE3",
        muted: "#8A8F85",
        neon: {
          emerald: "#3EFF9E",
          emeraldDeep: "#14B867",
          violet: "#B07CFF",
          violetDeep: "#7A3BFF",
          cyan: "#5EE1FF",
          cyanDeep: "#1BA6D4",
          red: "#FF5C5C",
          amber: "#FFB84D",
        },
      },
      fontFamily: {
        display: ["Space Grotesk", "system-ui", "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
      },
      letterSpacing: {
        tightish: "-0.02em",
      },
      boxShadow: {
        "bloom-emerald": "0 0 60px 0 rgba(62, 255, 158, 0.08)",
        "bloom-violet": "0 0 60px 0 rgba(176, 124, 255, 0.1)",
        "bloom-cyan": "0 0 60px 0 rgba(94, 225, 255, 0.1)",
        "glow-emerald": "0 0 15px 0 rgba(62, 255, 158, 0.35)",
        "glow-violet": "0 0 15px 0 rgba(176, 124, 255, 0.35)",
        "glow-cyan": "0 0 15px 0 rgba(94, 225, 255, 0.4)",
      },
      animation: {
        pulseDot: "pulseDot 1.6s ease-in-out infinite",
        shimmer: "shimmer 2s linear infinite",
      },
      keyframes: {
        pulseDot: {
          "0%, 100%": { opacity: "0.4", transform: "scale(0.9)" },
          "50%": { opacity: "1", transform: "scale(1.1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
