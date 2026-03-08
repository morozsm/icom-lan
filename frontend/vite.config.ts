/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  test: {
    environment: 'jsdom',
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/api/v1/ws': {
        target: 'ws://localhost:8080',
        ws: true,
        changeOrigin: true,
      },
      '/api/v1/scope': {
        target: 'ws://localhost:8080',
        ws: true,
        changeOrigin: true,
      },
      '/api/v1/meters': {
        target: 'ws://localhost:8080',
        ws: true,
        changeOrigin: true,
      },
      '/api/v1/audio': {
        target: 'ws://localhost:8080',
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
