/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        medibridge: {
          navy: '#1b5879',
          navyDark: '#14425b',
          sage: '#6b855d',
          sageDark: '#5c744f',
          lightBlue: '#e7f8fa',
          lightBlueHover: '#d9f2f5',
          bannerBg: '#f3fbfc',
        }
      },
      fontFamily: {
        serif: ['"Fraunces"', 'Georgia', 'serif'],
        sans: ['"Montserrat"', '-apple-system', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
