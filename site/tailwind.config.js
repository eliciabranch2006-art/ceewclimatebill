/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#EFF2ED",       // cool pale gray-green — "official record" backdrop
        ink: "#1F3A2E",         // deep forest ink — headings, primary accent
        inkmuted: "#4B5F55",
        amber: "#B8752B",       // score/attention accent, distinct from generic terracotta
        rule: "#C9D1C6",        // hairline divider color
        card: "#FBFAF6",
      },
      fontFamily: {
        display: ["Source Serif 4", "Georgia", "serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
