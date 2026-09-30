import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import fs from 'node:fs'
import path from 'node:path'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss()
  ],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        bypass: (req) => {
          const cleanPath = (req.url || '').split('?')[0];
          const localPath = path.join(process.cwd(), 'public', cleanPath);
          if (fs.existsSync(localPath) && fs.statSync(localPath).isFile()) {
            return req.url;
          }
          if (!cleanPath.endsWith('.json')) {
            const jsonPath = localPath + '.json';
            if (fs.existsSync(jsonPath) && fs.statSync(jsonPath).isFile()) {
              req.url = cleanPath + '.json';
              return req.url;
            }
          }
        }
      }
    }
  }
})
