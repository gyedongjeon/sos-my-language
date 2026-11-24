// Downloads the uv program that is shipped inside the packaged app (as Resources/uv/uv), so
// that users do not have to install uv themselves. Run by `npm run dist` and `npm run package`.
//
// The version and checksums are pinned: to update, change UV_VERSION and copy the new SHA-256
// values from the `.sha256` files of that release (https://github.com/astral-sh/uv/releases).
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { chmodSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const UV_VERSION = '0.13.9'
// Keyed by `${process.platform}-${process.arch}`; one entry per platform an installer is built for.
const BUILDS = {
  'darwin-arm64': {
    archive: 'uv-aarch64-apple-darwin.tar.gz',
    sha256: '5aeca67f2283f75235de40d0bd9c0a5bbc5fce23b6d48b3bf9fa1b2db08382ca',
  },
  'win32-x64': {
    archive: 'uv-x86_64-pc-windows-msvc.zip',
    sha256: 'edd61f7f5728a56cc62455386661860bdfc7bab65872f39b0c25bdcc1d8e1beb',
  },
}

const target = `${process.platform}-${process.arch}`
const build = BUILDS[target]
if (!build) {
  console.error(`No pinned uv build for ${target}. Add one to BUILDS in ${fileURLToPath(import.meta.url)}.`)
  process.exit(1)
}

const folder = join(dirname(fileURLToPath(import.meta.url)), '..', 'vendor', 'uv')
const program = join(folder, process.platform === 'win32' ? 'uv.exe' : 'uv')
const marker = join(folder, 'VERSION')
const wanted = `${UV_VERSION} ${target} ${build.sha256}`

if (existsSync(program) && existsSync(marker) && readFileSync(marker, 'utf8') === wanted) {
  console.log(`uv ${UV_VERSION} is already in ${folder}`)
  process.exit(0)
}

const url = `https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${build.archive}`
console.log(`Downloading ${url}`)
const response = await fetch(url)
if (!response.ok) {
  console.error(`Download failed: HTTP ${response.status}`)
  process.exit(1)
}
const archive = Buffer.from(await response.arrayBuffer())

// Nothing is unpacked or run unless the download is exactly the pinned release file.
const sha256 = createHash('sha256').update(archive).digest('hex')
if (sha256 !== build.sha256) {
  console.error(`Checksum mismatch for ${build.archive}:\n  expected ${build.sha256}\n  got      ${sha256}`)
  process.exit(1)
}

rmSync(folder, { recursive: true, force: true })
mkdirSync(folder, { recursive: true })
const archivePath = join(tmpdir(), `${sha256}-${build.archive}`)
writeFileSync(archivePath, archive)
try {
  if (build.archive.endsWith('.zip')) {
    // The Windows archive holds `uv.exe` and two helpers at its top; only `uv.exe` is needed.
    // Windows ships a tar that reads zip files. It is named by its full path, because a tar
    // from Git (first on the PATH of a Git shell) takes "C:" in a path for a remote host.
    const tar = join(process.env.SystemRoot ?? 'C:\\Windows', 'System32', 'tar.exe')
    execFileSync(tar, ['-xf', archivePath, '-C', folder, 'uv.exe'])
  } else {
    // The archive holds one folder with `uv` and `uvx`; only `uv` is needed.
    const inner = `${build.archive.replace(/\.tar\.gz$/, '')}/uv`
    execFileSync('tar', ['-xzf', archivePath, '-C', folder, '--strip-components=1', inner])
  }
} finally {
  rmSync(archivePath, { force: true })
}
if (!existsSync(program)) {
  console.error(`${build.archive} did not contain ${program}`)
  process.exit(1)
}
chmodSync(program, 0o755)
writeFileSync(marker, wanted)
console.log(`uv ${UV_VERSION} saved to ${program}`)
