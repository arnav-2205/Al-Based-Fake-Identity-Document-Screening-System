/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          950: '#060D1A',
          900: '#0A192F',
          850: '#0F203C',
          800: '#1E293B',
          700: '#334155',
          DEFAULT: '#0A192F',
        },
        tactical: {
          navy: '#0A192F',
          header: '#0D1C32',
          card: '#FFFFFF',
          border: '#DCE4EE',
          surface: '#F8FAFC',
          panel: '#F1F5F9',
        },
        status: {
          emerald: '#059669',
          'emerald-light': '#ECFDF5',
          'emerald-border': '#A7F3D0',
          amber: '#D97706',
          'amber-light': '#FFFBEB',
          'amber-border': '#FDE68A',
          rose: '#DC2626',
          'rose-light': '#FEF2F2',
          'rose-border': '#FECACA',
          sky: '#0284C7',
          'sky-light': '#F0F9FF',
          'sky-border': '#BAE6FD',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'SFMono-Regular', 'Menlo', 'monospace'],
        display: ['Space Grotesk', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
