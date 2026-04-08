import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f6f2e8",
        ink: "#172027",
        accent: "#1d6f5f",
        sand: "#d9c8aa",
        alert: "#9b2c2c",
      },
      fontFamily: {
        sans: ["Assistant", "Segoe UI", "sans-serif"],
        display: ["Heebo", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        card: "0 14px 30px rgba(23, 32, 39, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
