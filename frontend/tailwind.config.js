/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#101114",
        smoke: "#6f7787",
        surface: "#f5f7fb",
        card: "#ffffff",
        accent: "#111827",
        blush: "#ffe7ea",
        ok: "#0f9f76",
        warn: "#e58f15",
        danger: "#e23d5a",
        cyber: {
          void: "#060812",
          panel: "#0d1224",
          line: "#1d2a4a",
          cyan: "#38bdf8",
          violet: "#8b5cf6",
          magenta: "#d946ef"
        }
      },
      fontFamily: {
        sans: ["'Plus Jakarta Sans'", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["'Space Grotesk'", "'Plus Jakarta Sans'", "ui-sans-serif", "system-ui", "sans-serif"]
      },
      boxShadow: {
        soft: "0 24px 80px rgba(0, 0, 0, 0.34)",
        float: "0 28px 80px rgba(15, 23, 42, 0.42)",
        glow: "0 0 34px rgba(56, 189, 248, 0.24), 0 0 70px rgba(139, 92, 246, 0.18)"
      },
      backgroundImage: {
        grid: "radial-gradient(circle at 1px 1px, rgba(15, 23, 42, 0.08) 1px, transparent 0)"
      },
      keyframes: {
        rise: {
          "0%": { opacity: 0, transform: "translateY(14px)" },
          "100%": { opacity: 1, transform: "translateY(0)" }
        },
        pulsebar: {
          "0%, 100%": { transform: "scaleY(0.55)" },
          "50%": { transform: "scaleY(1)" }
        },
        scanline: {
          "0%": { left: "-45%" },
          "52%, 100%": { left: "110%" }
        },
        glowPulse: {
          "0%, 100%": { opacity: "0.55", boxShadow: "0 0 0 rgba(56, 189, 248, 0)" },
          "50%": { opacity: "1", boxShadow: "0 0 24px rgba(56, 189, 248, 0.5)" }
        }
      },
      animation: {
        rise: "rise 0.6s ease forwards",
        pulsebar: "pulsebar 1s ease-in-out infinite",
        scanline: "scanline 4.5s ease-in-out infinite",
        glowPulse: "glowPulse 2s ease-in-out infinite"
      }
    }
  },
  plugins: []
};
