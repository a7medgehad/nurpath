import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        desert: "#A2673F",
        ink: "#1A1E2A",
        oasis: "#007D7D",
        sand: "#F5EDE2",
      },
      boxShadow: {
        soft: "0 10px 40px rgba(0,0,0,0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
