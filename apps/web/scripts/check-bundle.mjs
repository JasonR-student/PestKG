import { readdir, stat } from 'node:fs/promises'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const assetDirectory = fileURLToPath(new URL('../dist/assets/', import.meta.url))
const maximumBytes = 500 * 1024
const files = await readdir(assetDirectory)
const oversized = []

for (const file of files.filter((name) => name.endsWith('.js'))) {
  const size = (await stat(join(assetDirectory, file))).size
  if (size > maximumBytes) oversized.push({ file, size })
}

if (oversized.length) {
  for (const item of oversized) {
    console.error(`${item.file}: ${item.size} bytes exceeds ${maximumBytes}`)
  }
  process.exitCode = 1
} else {
  console.log(`Bundle check passed: every JavaScript chunk is <= ${maximumBytes} bytes`)
}
