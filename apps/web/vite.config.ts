import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: 'zrender',
              test: /node_modules[\\/]zrender[\\/]/,
              includeDependenciesRecursively: false,
            },
            {
              name: 'echarts',
              test: /node_modules[\\/]echarts[\\/]/,
              includeDependenciesRecursively: false,
              maxSize: 450 * 1024,
            },
          ],
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '^/downloads/.+': 'http://127.0.0.1:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    include: ['./src/**/*.test.{ts,tsx}'],
    css: true,
  },
})
