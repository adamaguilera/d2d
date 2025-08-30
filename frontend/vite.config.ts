import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteStaticCopy } from 'vite-plugin-static-copy'
import path from 'path'
import sirv from 'sirv'
import fs from 'fs'
import fsp from 'fs/promises'
import { fileURLToPath } from 'url'

// https://vite.dev/config/
export default defineConfig(() => {
  const thisFilePath = fileURLToPath(import.meta.url)
  const thisDir = path.dirname(thisFilePath)
  const repoRoot = path.resolve(thisDir, '..')
  const contentDir = path.resolve(repoRoot, 'content')

  async function generateHeroesManifest(): Promise<void> {
    const heroesDir = path.join(contentDir, 'images', 'heroes')
    const outDir = path.join(thisDir, 'public', 'data')
    const outFile = path.join(outDir, 'heroes.json')
    try {
      fs.mkdirSync(outDir, { recursive: true })
      const files: string[] = await fsp.readdir(heroesDir)
      const heroes = files
        .filter((f: string) => f.toLowerCase().endsWith('.png'))
        .map((filename: string) => {
          const slug = filename.replace(/\.png$/i, '')
          const name = slug
            .split('-')
            .map((s: string) => s.charAt(0).toUpperCase() + s.slice(1))
            .join(' ')
          return {
            slug,
            name,
            image: `/content/images/heroes/${filename}`,
          }
        })
        .sort((a: { name: string }, b: { name: string }) => a.name.localeCompare(b.name))
      await fsp.writeFile(outFile, JSON.stringify({ heroes }, null, 2), 'utf-8')
      // eslint-disable-next-line no-console
      console.log(`Generated heroes manifest at ${path.relative(repoRoot, outFile)}`)
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('Failed to generate heroes manifest', err)
    }
  }

  return {
    base: './',
    plugins: [
      react(),
      viteStaticCopy({
        targets: [
          {
            src: contentDir,
            dest: '.',
          },
        ],
      }),
      {
        name: 'serve-content-dir',
        configureServer(server) {
          // Serve /content/* from the monorepo during dev
          server.middlewares.use('/content', sirv(contentDir, { dev: true }))
        },
      },
      {
        name: 'generate-heroes-manifest',
        buildStart: generateHeroesManifest,
        configureServer() {
          generateHeroesManifest()
        },
      },
    ],
    server: {
      fs: {
        allow: [repoRoot],
      },
    },
  }
})
