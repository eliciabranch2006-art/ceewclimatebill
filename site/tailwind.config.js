/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // CEEW brand palette: white, black, orange, blue, green.
        paper: "#FFFFFF",
        ink: "#000000",
        inkmuted: "#5C5C5C",    // structural gray for secondary text — not a brand color,
                                 // needed so body copy isn't pure black-on-white everywhere
        rule: "#E4E4E4",        // structural gray for hairline dividers, same reasoning
        card: "#FFFFFF",
        orange: "#F16223",      // primary accent — CTAs, "needs review" flags
        blue: "#009ED8",        // links, interactive/filter states
        green: "#86BB3F",       // positive signal — high scores, "Passed" status
        amber: "#F16223",       // kept as an alias so existing className references still work
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
