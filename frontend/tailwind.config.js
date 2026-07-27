/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["DM Sans", "system-ui", "sans-serif"],
        display: ["Outfit", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      colors: {
        surface: {
          950: "#080a0e",
          900: "#0c0f14",
          800: "#121820",
          700: "#1a2230",
          600: "#243044",
          500: "#334155",
        },
        accent: {
          DEFAULT: "#22d3ee",
          muted: "#0891b2",
          glow: "#67e8f9",
        },
        stream: {
          done: "#34d399",
          active: "#22d3ee",
          wait: "#64748b",
          error: "#f87171",
        },
      },
      boxShadow: {
        panel: "0 0 0 1px rgba(148, 163, 184, 0.08), 0 24px 48px -12px rgba(0, 0, 0, 0.45)",
      },
      animation: {
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
      },
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.45" },
        },
      },
    },
  },
  plugins: [],
};
