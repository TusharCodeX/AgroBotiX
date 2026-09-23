/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        crop: '#22c55e',
        weed: '#ef4444',
        uncertain: '#eab308',
      },
    },
  },
  plugins: [],
}
