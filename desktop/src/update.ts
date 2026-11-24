// In-app updates without an Apple developer signature: find a newer GitHub release, download
// its archive, check it against the checksum GitHub reports, and swap the app bundle.
//
// Nothing here imports Electron, so it can be tested and run with plain Node.
import { execFile, spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { createWriteStream, type WriteStream } from 'node:fs'
import { readdir, rm } from 'node:fs/promises'
import { dirname, join, sep } from 'node:path'
import { promisify } from 'node:util'

const run = promisify(execFile)

const REPOSITORY = 'gyedongjeon/sos-my-english'
export const LATEST_RELEASE_API = `https://api.github.com/repos/${REPOSITORY}/releases/latest`
export const RELEASES_PAGE = `https://github.com/${REPOSITORY}/releases/latest`
// Downloads and links are accepted only from this project's releases.
const DOWNLOAD_PREFIX = `https://github.com/${REPOSITORY}/releases/download/`
const RELEASE_PAGE_PREFIX = `https://github.com/${REPOSITORY}/releases/`

export interface Archive {
  url: string
  /** Hex SHA-256 the download must have. */
  sha256: string
  size: number
}

export interface Update {
  version: string
  /** The release page, for reading what changed or downloading by hand. */
  notesUrl: string
  /** The archive this app can install by itself; null when the user has to download the release. */
  archive: Archive | null
}

type Fetch = (url: string, init?: { headers?: Record<string, string> }) => Promise<Response>

function parseVersion(version: string): number[] | null {
  return /^\d+\.\d+\.\d+$/.test(version) ? version.split('.').map(Number) : null
}

/** Whether `candidate` is a later x.y.z version than `current`. */
export function isNewer(candidate: string, current: string): boolean {
  const a = parseVersion(candidate)
  const b = parseVersion(current)
  if (!a || !b) return false
  for (let i = 0; i < 3; i++) if (a[i] !== b[i]) return a[i] > b[i]
  return false
}

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null

/**
 * The update a "latest release" reply from GitHub offers to an app at version `current`, or
 * null when there is none. The reply comes from the network, so every field is checked.
 */
export function findUpdate(release: unknown, current: string, arch: string): Update | null {
  if (!isRecord(release) || release.draft !== false || release.prerelease !== false) return null
  const tag = typeof release.tag_name === 'string' ? release.tag_name : ''
  const version = tag.replace(/^v/, '')
  if (!tag.startsWith('v') || !isNewer(version, current)) return null

  const page = release.html_url
  const notesUrl = typeof page === 'string' && page.startsWith(RELEASE_PAGE_PREFIX) ? page : RELEASES_PAGE

  const assets = Array.isArray(release.assets) ? release.assets.filter(isRecord) : []
  const suffix = `-${arch}-mac.zip`
  let archive: Archive | null = null
  for (const asset of assets) {
    const { name, state, digest, size, browser_download_url: url } = asset
    if (typeof name !== 'string' || !name.endsWith(suffix) || state !== 'uploaded') continue
    if (typeof url !== 'string' || !url.startsWith(DOWNLOAD_PREFIX)) continue
    // Without a checksum the download cannot be verified, so it is not installed automatically.
    const sha256 = typeof digest === 'string' ? /^sha256:([0-9a-f]{64})$/.exec(digest)?.[1] : undefined
    if (!sha256 || typeof size !== 'number') continue
    archive = { url, sha256, size }
    break
  }
  return { version, notesUrl, archive }
}

/** Ask GitHub for the latest release. Throws when the request fails. */
export async function fetchLatestRelease(fetchImpl: Fetch, userAgent: string): Promise<unknown> {
  const response = await fetchImpl(LATEST_RELEASE_API, {
    headers: { Accept: 'application/vnd.github+json', 'User-Agent': userAgent },
  })
  if (!response.ok) throw new Error(`GitHub answered HTTP ${response.status}`)
  return response.json()
}

/** The `.app` folder containing the running program, or null when it is not in one. */
export function bundlePath(exe: string): string | null {
  const macos = dirname(exe)
  const contents = dirname(macos)
  const bundle = dirname(contents)
  const inBundle = macos.endsWith(`${sep}MacOS`) && contents.endsWith(`${sep}Contents`) && bundle.endsWith('.app')
  return inBundle ? bundle : null
}

export interface Installation {
  packaged: boolean
  platform: NodeJS.Platform
  bundle: string | null
  /** Whether a folder can be written to. */
  writable: (folder: string) => boolean
}

/** Why this copy of the app cannot replace itself, or null when it can. */
export function replaceBlocker({ packaged, platform, bundle, writable }: Installation): string | null {
  if (platform !== 'darwin') return 'On this system the new version is installed with its installer from the download page.'
  if (!packaged) return 'This copy runs from a source checkout; update it with git.'
  if (!bundle) return 'The app is not running from an app bundle.'
  // A quarantined app that was never moved runs from a random read-only place ("translocation"),
  // and an app opened straight from the disk image runs from a read-only volume.
  if (bundle.includes('/AppTranslocation/') || bundle.startsWith('/Volumes/')) {
    return 'Move the app to the Applications folder first, then open it from there.'
  }
  if (!writable(bundle) || !writable(dirname(bundle))) {
    return 'The app does not have permission to replace itself in this folder.'
  }
  return null
}

/**
 * Download an archive to `dest` and check its SHA-256. A download that fails or does not match
 * is deleted and the promise rejects, so a file at `dest` is always the verified archive.
 */
export async function download(
  archive: Archive,
  dest: string,
  fetchImpl: Fetch,
  onProgress?: (fraction: number) => void,
): Promise<void> {
  const hash = createHash('sha256')
  let file: WriteStream | null = null
  try {
    const response = await fetchImpl(archive.url)
    if (!response.ok || !response.body) throw new Error(`The download failed: HTTP ${response.status}`)
    file = createWriteStream(dest)
    let received = 0
    for await (const chunk of response.body as unknown as AsyncIterable<Uint8Array>) {
      hash.update(chunk)
      received += chunk.length
      if (!file.write(chunk)) await new Promise((resolve) => file!.once('drain', resolve))
      onProgress?.(archive.size ? Math.min(received / archive.size, 1) : 0)
    }
    await new Promise<void>((resolve, reject) => file!.end((error?: Error | null) => (error ? reject(error) : resolve())))
    const sha256 = hash.digest('hex')
    if (sha256 !== archive.sha256) {
      throw new Error(`The download does not match its checksum (expected ${archive.sha256}, got ${sha256}).`)
    }
  } catch (error) {
    // Wait until the file is closed: removing it while it is still being opened would leave it behind.
    if (file && !file.closed) {
      await new Promise((resolve) => file!.once('close', resolve).destroy())
    }
    await rm(dest, { force: true })
    throw error
  }
}

/**
 * Replaces the app once it has quit, then opens it again. Arguments: the app's process id, the
 * installed bundle, the new bundle, a path for a temporary backup, then the command that opens
 * an app (the installed bundle's path is appended to it).
 *
 * The old bundle is only removed after the new one is in place; if moving the new one in fails,
 * the old one is put back, so there is always an app to open.
 */
export const SWAP_SCRIPT = `
pid="$1"; current="$2"; next="$3"; backup="$4"; shift 4

# Wait for the app to quit (60 s at most), so that its files are no longer in use.
tries="\${SWAP_WAIT_TRIES:-300}"
while kill -0 "$pid" 2>/dev/null && [ "$tries" -gt 0 ]; do
  sleep 0.2
  tries=$((tries - 1))
done
if kill -0 "$pid" 2>/dev/null; then
  exit 1
fi

rm -rf "$backup"
if [ -d "$next" ] && mv "$current" "$backup"; then
  if mv "$next" "$current"; then
    rm -rf "$backup"
  else
    mv "$backup" "$current"
  fi
fi

"$@" "$current"
`

/** Start the swap in a process of its own, which outlives the app. The app must quit right after. */
export function swapAfterQuit(pid: number, current: string, next: string, backup: string, reopen: string[]): void {
  const child = spawn('/bin/bash', ['-c', SWAP_SCRIPT, 'swap', String(pid), current, next, backup, ...reopen], {
    detached: true,
    stdio: 'ignore',
  })
  child.unref()
}

export interface BundleInfo {
  id: string
  version: string
}

/** The identifier and version written in an app bundle's Info.plist. */
export async function readBundleInfo(bundle: string): Promise<BundleInfo> {
  const plist = join(bundle, 'Contents', 'Info.plist')
  const read = async (key: string) => (await run('/usr/bin/plutil', ['-extract', key, 'raw', plist])).stdout.trim()
  return { id: await read('CFBundleIdentifier'), version: await read('CFBundleShortVersionString') }
}

/**
 * Unpack a downloaded archive into `dir` and return the app bundle inside it. Rejects unless
 * the bundle is the expected app at the expected version with an intact code signature, so a
 * wrong or damaged archive never replaces the installed app.
 */
export async function unpackBundle(zip: string, dir: string, expected: BundleInfo): Promise<string> {
  // ditto keeps the symbolic links and permissions that an app bundle depends on.
  await run('/usr/bin/ditto', ['-x', '-k', zip, dir])
  const name = (await readdir(dir)).find((entry) => entry.endsWith('.app'))
  if (!name) throw new Error('The archive does not contain an app.')
  const bundle = join(dir, name)
  const info = await readBundleInfo(bundle)
  if (info.id !== expected.id || info.version !== expected.version) {
    throw new Error(`The archive contains ${info.id} ${info.version}, not ${expected.id} ${expected.version}.`)
  }
  await run('/usr/bin/codesign', ['--verify', '--deep', bundle])
  return bundle
}
