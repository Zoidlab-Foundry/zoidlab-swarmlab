/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#12100a", panel: "#1c1810", panel2: "#251f14", line: "#3a301d",
        cy: "#fde68a", vi: "#fbbf24", ind: "#f59e0b", prism: "#fbbf24",
        ink: "#f5efe2", dim: "#c2b291", faint: "#8a7a5c",
        ok: "#22c55e", warn: "#f4b860", bad: "#ef4444",
      },
      boxShadow: {
        glow: "0 0 40px -10px rgba(251,191,36,0.40)",
      },
    },
  },
  plugins: [],
};
