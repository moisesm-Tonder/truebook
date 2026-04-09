/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        tonder: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#375DFB',
          600: '#2c4fd4',
          700: '#2241b0',
          800: '#1a348d',
          900: '#112070',
          950: '#0a1445',
        },
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '12px',
      },
      boxShadow: {
        'tonder': '0 0 0 1px rgba(55,93,251,0.15), 0 4px 24px rgba(55,93,251,0.10)',
        'card': '0 1px 3px rgba(0,0,0,0.3), 0 8px 32px rgba(0,0,0,0.2)',
      },
    },
  },
  plugins: [],
}
