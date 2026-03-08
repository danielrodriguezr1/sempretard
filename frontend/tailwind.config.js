/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#F4F1F8",
        card: "#FFFFFF",
        ink: "#2E2E2E",
        muted: "#6B7280",
        edge: "#E5E7EB",
        // Modo colors (pastel identities)
        "m-coche":   "#D6E4F0",
        "m-metro":   "#DDD5F3",
        "m-bus":     "#D5EDE2",
        "m-tren":    "#F5D5D5",
        // Primary palette
        primary:   "#8FAADC",
        secondary: "#C6B8F3",
        accent:    "#F2C6D6",
        // Status
        ok:   "#6DBB8B",
        warn: "#E0A458",
        bad:  "#D46B6B",
      },
    },
  },
  plugins: [],
};
