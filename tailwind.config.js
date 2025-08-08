/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,js}"],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        vercel: {
          dark: '#000000',
          light: '#ffffff',
          gray: {
            50: '#fafafa',
            100: '#f5f5f5',
            200: '#eaeaea',
            300: '#d4d4d4',
            500: '#737373',
            700: '#404040',
            800: '#262626',
            900: '#171717',
          },
          blue: {
            500: '#0070f3',
            600: '#0061d6',
            700: '#0051b3',
          },
          purple: {
            500: '#7928ca',
            600: '#641fc9',
          },
          pink: {
            500: '#ff0080',
            600: '#e60073',
          }
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'Noto Sans', 'sans-serif'],
        mono: ['Menlo', 'Monaco', 'Lucida Console', 'Liberation Mono', 'DejaVu Sans Mono', 'Bitstream Vera Sans Mono', 'Courier New', 'monospace'],
      },
      boxShadow: {
        'card': '0 4px 12px rgba(0, 0, 0, 0.08)',
        'card-hover': '0 8px 24px rgba(0, 0, 0, 0.12)',
      },
      borderRadius: {
        'lg': '0.625rem',
        'xl': '0.75rem',
        '2xl': '1rem',
      },
      transitionTimingFunction: {
        'in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
    },
  },
  plugins: [],
}