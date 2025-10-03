/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "white",
        foreground: "black",
        card: {
          DEFAULT: "rgb(250 250 250)",
          foreground: "black",
        },
        primary: {
          DEFAULT: "black",
          foreground: "white",
        },
        secondary: {
          DEFAULT: "rgb(245 245 245)",
          foreground: "black",
        },
        muted: {
          DEFAULT: "rgb(245 245 245)",
          foreground: "rgb(115 115 115)",
        },
        accent: {
          DEFAULT: "rgb(245 245 245)",
          foreground: "black",
        },
        border: "rgb(229 229 229)",
        input: "rgb(229 229 229)",
        ring: "black",
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}