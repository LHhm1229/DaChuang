/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          dryeye: '#16C79E',
          sleep: '#4F1091',
          fatigue: '#E86830'
        },
        secondary: {
          dryeye: '#0F8C6E',
          sleep: '#3A0C6E',
          fatigue: '#C75425'
        },
        background: {
          dryeye: '#F0FAF7',
          sleep: '#1A0535',
          fatigue: '#FFF8F5'
        },
        card: {
          dryeye: 'rgba(255, 255, 255, 0.1)',
          sleep: 'rgba(255, 255, 255, 0.1)',
          fatigue: 'rgba(255, 255, 255, 0.1)'
        }
      },
      backdropBlur: {
        xs: '2px',
      }
    },
  },
  plugins: [],
}