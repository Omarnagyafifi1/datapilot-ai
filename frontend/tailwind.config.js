/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: "var(--card)",
        cyber: {
          cyan: "var(--cyber-cyan)",
          pink: "var(--cyber-pink)",
          lime: "var(--cyber-lime)",
          blue: "var(--cyber-blue)",
        },
        border: "var(--border)",
        muted: "var(--muted)",
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
