import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const apiTarget = env.VITE_API_URL?.trim() || 'http://localhost:8000'

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        // The browser always calls same-origin /api paths. During local
        // development only, Vite forwards them to this backend target.
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
