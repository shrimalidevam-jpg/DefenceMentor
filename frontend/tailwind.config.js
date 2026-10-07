/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        nda: {
          primary: '#1e3a5f',
          secondary: '#2c5282',
          accent: '#3182ce',
          light: '#ebf8ff',
          dark: '#0f172a',
        },
      },
    },
  },
  plugins: [],
}
