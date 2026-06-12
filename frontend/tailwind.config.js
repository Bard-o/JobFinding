/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0a0a0a',
        card: '#171717',
        'card-foreground': '#fafafa',
        border: '#262626',
        muted: '#a3a3a3',
        accent: '#f97316',
        'accent-foreground': '#fafafa',
      },
    },
  },
  plugins: [],
}