// Puts the Python that the backend runs on into the packaged Windows app (as resources/python),
// so that the first launch does not have to download it. Run by `npm run dist` after fetch-uv.
//
// Only Windows gets it: there, the download stalled on every first launch that was tried, while
// the macOS app has always fetched its Python without trouble.
import { execFileSync } from 'node:child_process'
import { existsSync, lstatSync, readdirSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

if (process.platform !== 'win32') {
  console.log('Python is shipped only in the Windows app; nothing to do here.')
  process.exit(0)
}

const desktop = join(dirname(fileURLToPath(import.meta.url)), '..')
const uv = join(desktop, 'vendor', 'uv', 'uv.exe')
// The same pin that uv follows when it picks a Python by itself.
const version = readFileSync(join(desktop, '..', 'backend', '.python-version'), 'utf8').trim()
const folder = join(desktop, 'vendor', 'python')
const marker = join(folder, 'VERSION')

if (existsSync(join(folder, 'python.exe')) && existsSync(marker) && readFileSync(marker, 'utf8') === version) {
  console.log(`Python ${version} is already in ${folder}`)
  process.exit(0)
}

// uv installs into a folder named after the exact build and adds a link beside it; the app
// needs one fixed path, so the installed folder is moved out and the rest is dropped.
const staging = join(desktop, 'vendor', 'python-staging')
rmSync(staging, { recursive: true, force: true })
rmSync(folder, { recursive: true, force: true })
execFileSync(uv, ['python', 'install', version, '--install-dir', staging], {
  stdio: 'inherit',
  // Nothing outside the staging folder: no launcher in the home folder, no registry entry.
  env: { ...process.env, UV_PYTHON_INSTALL_BIN: '0', UV_PYTHON_INSTALL_REGISTRY: '0' },
})
const installed = readdirSync(staging)
  .map((name) => join(staging, name))
  .find((path) => lstatSync(path).isDirectory() && existsSync(join(path, 'python.exe')))
if (!installed) {
  console.error(`uv did not leave a Python in ${staging}`)
  process.exit(1)
}
renameSync(installed, folder)
rmSync(staging, { recursive: true, force: true })
writeFileSync(marker, version)
console.log(`Python ${version} saved to ${folder}`)
