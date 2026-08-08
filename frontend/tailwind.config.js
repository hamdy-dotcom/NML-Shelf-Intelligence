/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Noto Kufi Arabic', 'Noto Sans Arabic', 'Segoe UI', 'system-ui', 'sans-serif'],
      },
      colors: {
        accent: '#ed1c24',
      },
      borderRadius: {
        card: '18px',
        icon: '12px',
        pill: '999px',
      },
    },
  },
  plugins: [],
}
