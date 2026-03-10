/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0a0a0a',
        surface: '#161616',
        card: '#1c1c1e',
        border: '#2a2a2a',
        cyan: {
          DEFAULT: '#5ce1e6',
          dim: 'rgba(92,225,230,0.15)',
        },
        text: {
          primary: '#ffffff',
          secondary: '#8e8e93',
          muted: '#48484a',
        },
        lab: '#4ade80',
        lecture: '#60a5fa',
        seminar: '#fb923c',
        practice: '#a78bfa',
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'monospace'],
      },
      borderRadius: {
        xl: '16px',
        '2xl': '20px',
        '3xl': '24px',
      },
    },
  },
  plugins: [],
}
