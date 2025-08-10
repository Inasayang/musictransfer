/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'vercel-gray': {
          100: '#fafafa',
          400: '#a3a3a3',
          500: '#737373',
          600: '#525252',
          700: '#404040',
          800: '#262626',
          900: '#171717',
        },
        'vercel-blue': {
          500: '#0070f3',
          600: '#0061d6',
        },
        'vercel-purple': {
          500: '#7928ca',
          600: '#6b21d6',
        },
      },
      fontFamily: {
        'sans': ['Inter', 'ui-sans-serif', 'system-ui'],
      },
      boxShadow: {
        'card': '0 4px 14px 0 rgba(0, 0, 0, 0.1)',
        'card-hover': '0 6px 20px 0 rgba(0, 0, 0, 0.15)',
      },
    },
  },
  plugins: [require("daisyui")],
  daisyui: {
    themes: [
      {
        light: {
          ...require("daisyui/src/theming/themes")["light"],
          primary: "#0070f3",
          secondary: "#7928ca",
          accent: "#10b981",
          neutral: "#171717",
          "base-100": "#ffffff",
          "base-200": "#f8f8f8",
          "base-300": "#e5e5e5",
        },
        dark: {
          ...require("daisyui/src/theming/themes")["dark"],
          primary: "#0070f3",
          secondary: "#7928ca",
          accent: "#10b981",
          neutral: "#262626",
          "base-100": "#000000",
          "base-200": "#171717",
          "base-300": "#262626",
        },
      },
    ],
  },
}