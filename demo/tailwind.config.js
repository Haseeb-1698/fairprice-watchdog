/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Dark regtech base
        ink: {
          900: "#05070D", // page background
          800: "#0A0E1A", // panel
          700: "#11162A", // raised panel
          600: "#1A2138", // border-ish
        },
        // Gold = brand / authority
        gold: {
          400: "#F4C752",
          500: "#D4AF37",
          600: "#A8841F",
        },
        fair: "#22C55E", // green = fair / savings
        violation: "#EF4444", // red = junk fee / violation
        warn: "#F59E0B",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["'Space Grotesk'", "Inter", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      boxShadow: {
        gold: "0 0 0 1px rgba(212,175,55,0.25), 0 8px 40px -8px rgba(212,175,55,0.25)",
        panel: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 20px 60px -20px rgba(0,0,0,0.8)",
      },
      keyframes: {
        shimmer: { "100%": { transform: "translateX(100%)" } },
        pulseRing: {
          "0%": { boxShadow: "0 0 0 0 rgba(212,175,55,0.5)" },
          "70%": { boxShadow: "0 0 0 10px rgba(212,175,55,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(212,175,55,0)" },
        },
      },
      animation: {
        shimmer: "shimmer 1.6s infinite",
        pulseRing: "pulseRing 1.8s infinite",
      },
    },
  },
  plugins: [],
};
