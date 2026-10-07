import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const certificatePath = fileURLToPath(new URL('./.cert/localhost.pem', import.meta.url))
const privateKeyPath = fileURLToPath(new URL('./.cert/localhost-key.pem', import.meta.url))
const hasLocalCertificate = existsSync(certificatePath) && existsSync(privateKeyPath)

if (!hasLocalCertificate) {
  console.warn('Local HTTPS certificate not found. Vite will use HTTP; see the README to enable trusted HTTPS with mkcert.')
}

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    https: hasLocalCertificate
      ? {
          cert: readFileSync(certificatePath),
          key: readFileSync(privateKeyPath),
        }
      : undefined,
    headers: {
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
      'Permissions-Policy': 'camera=(), microphone=(self), geolocation=()',
      ...(hasLocalCertificate ? { 'Strict-Transport-Security': 'max-age=31536000' } : {}),
    },
    proxy: {
      // Proxy /api requests to FastAPI backend during development
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
