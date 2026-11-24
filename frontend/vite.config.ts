import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    // Forward API calls to the FastAPI dev server to avoid CORS setup.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
