/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', '"Prompt"', 'system-ui', 'sans-serif'],
        display: ['"Plus Jakarta Sans"', '"Prompt"', 'sans-serif'],
      },
      colors: {
        pantone: {
          50: '#f2f4fb',
          100: '#e3e7f7',
          200: '#cbd4f1',
          300: '#a7b7e6',
          400: '#7e93d8',
          500: '#5e72c8',
          600: '#4655b3',
          700: '#38439b',
          800: '#262f68',
          900: '#131936', // Requested Pantone Hex
          950: '#0b0f22',
        },
        brand: {
          50: '#f2f4fb',
          100: '#e3e7f7',
          500: '#4655b3',
          600: '#262f68',
          700: '#1c244b',
          800: '#131936',
          900: '#0b0f22',
        }
      }
    },
  },
  plugins: [],
}
