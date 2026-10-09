/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          950: '#070b14',
          900: '#0b1120',
          850: '#111827',
          800: '#17223b',
          700: '#1e293b',
          600: '#334155',
        },
        emerald: {
          accent: '#10b981',
          hover: '#059669',
          glow: 'rgba(16, 185, 129, 0.15)',
        },
        teal: {
          accent: '#14b8a6',
          hover: '#0d9488',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
