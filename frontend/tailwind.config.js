/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#050505",
        foreground: "#ffffff",
        card: "#0a0a0a",
        cyber: {
          cyan: "#00f2ff",
          pink: "#ff00ff",
          lime: "#ccff00",
          blue: "#0070ff",
        },
        border: "#1a1a1a",
        muted: "#666666",
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Roboto Mono', 'monospace'],
        sans: ['Inter', 'sans-serif'],
      },
      boxShadow: {
        'glow-cyan': '0 0 10px rgba(0, 242, 255, 0.3)',
        'glow-lime': '0 0 10px rgba(204, 255, 0, 0.3)',
      }
    },
  },
  plugins: [],
}
