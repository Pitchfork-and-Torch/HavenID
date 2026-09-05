import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Satoshi", "system-ui", "sans-serif"],
        display: ["Clash Display", "Satoshi", "system-ui", "sans-serif"],
      },
      colors: {
        ink: {
          950: "#12110f",
          900: "#181714",
          800: "#221f1b",
          700: "#2d2924",
        },
        gold: {
          400: "#e2b657",
          500: "#c89a3a",
          600: "#a67c28",
        },
      },
      boxShadow: {
        focus: "0 0 0 2px var(--bg), 0 0 0 4px var(--accent)",
      },
    },
  },
  plugins: [],
};

export default config;
