import { defineConfig } from '@hey-api/openapi-ts'

export default defineConfig({
  input: '../../packages/api-contract/graph-browser-v1.yaml',
  output: 'src/shared/api/browser-generated',
  plugins: ['@hey-api/typescript'],
})
