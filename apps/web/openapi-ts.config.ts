import { defineConfig } from '@hey-api/openapi-ts'

export default defineConfig({
  input: '../../packages/api-contract/openapi-v1.1.json',
  output: 'src/shared/api/generated',
  plugins: ['@hey-api/typescript'],
})
