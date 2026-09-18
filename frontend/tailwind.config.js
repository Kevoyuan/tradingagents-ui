/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "#ffffff",
        page: "#f2f1ee",
        rule: "#dcdad4",
        "rule-2": "#ebe9e4",
        ink: "#0a0a0a",
        "ink-2": "#3d3a35",
        mut: "#6e6a63",
        faint: "#9c978e",
        buy: "#0b6b3a",
        sell: "#a8121f",
        hold: "#545049",
      },
      fontFamily: {
        grotesk: ['Archivo', '"Helvetica Neue"', 'Helvetica', 'Arial', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      letterSpacing: {
        cap: '0.13em',
        wide2: '0.15em',
      },
    },
  },
  plugins: [],
};
