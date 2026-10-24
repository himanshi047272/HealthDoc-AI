export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: { cream: '#FBF3E4', ink: '#141414', sand: '#EFE6D2', sun: '#F5D654', rose: '#F4B4D0', moss: '#9FB26A', sky: '#B5C7EE' },
      fontFamily: { sans: ['"DM Sans"', 'Inter', 'system-ui', 'sans-serif'] },
      borderRadius: { card: '22px' },
    },
  },
  plugins: [],
}
