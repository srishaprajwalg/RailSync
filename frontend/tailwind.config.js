/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        rail: {
          blue: '#0B3A5B',
          saffron: '#F28C28',
          green: '#16834B',
          bg: '#F7F8FA',
          white: '#FFFFFF',
          'text-dark': '#17202A',
          'text-muted': '#64748B',
          border: '#E2E8F0',
          warning: '#D97706',
          error: '#DC2626',
        }
      }
    },
  },
  plugins: [],
}
