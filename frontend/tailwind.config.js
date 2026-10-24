/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#06101f",
        panel: "#0a1728",
        cyan: "#49dcff",
        violet: "#9b7cff",
        gold: "#f8c761"
      },
      fontFamily: { sans: ["Inter", "Segoe UI", "sans-serif"], display: ["Space Grotesk", "Segoe UI", "sans-serif"] }
    }
  },
  plugins: []
};

