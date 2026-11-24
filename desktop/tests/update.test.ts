import { spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { bundlePath, download, findUpdate, isNewer, replaceBlocker, SWAP_SCRIPT } from '../src/update'

const DOWNLOADS = 'https://github.com/gyedongjeon/sos-my-language/releases/download'
const SHA = 'a'.repeat(64)

// The parts of GitHub's "latest release" reply that the updater reads.
const release = (overrides: Record<string, unknown> = {}, assets?: Record<string, unknown>[]) => ({
  tag_name: 'v0.3.0',
  draft: false,
  prerelease: false,
  html_url: 'https://github.com/gyedongjeon/sos-my-language/releases/tag/v0.3.0',
  assets: assets ?? [
    { name: 'SOS.My.Language-0.3.0-arm64.dmg', state: 'uploaded', size: 1, digest: `sha256:${'b'.repeat(64)}`, browser_download_url: `${DOWNLOADS}/v0.3.0/SOS.My.Language-0.3.0-arm64.dmg` },
    { name: 'SOS.My.Language-0.3.0-arm64-mac.zip', state: 'uploaded', size: 1234, digest: `sha256:${SHA}`, browser_download_url: `${DOWNLOADS}/v0.3.0/SOS.My.Language-0.3.0-arm64-mac.zip` },
  ],
  ...overrides,
})

describe('isNewer', () => {
  it('compares each part as a number', () => {
    expect(isNewer('0.3.0', '0.2.1')).toBe(true)
    expect(isNewer('0.10.0', '0.9.9')).toBe(true)
    expect(isNewer('1.0.0', '0.99.99')).toBe(true)
    expect(isNewer('0.2.1', '0.2.1')).toBe(false)
    expect(isNewer('0.2.0', '0.2.1')).toBe(false)
  })

  it('ignores anything that is not a plain x.y.z version', () => {
    expect(isNewer('0.3.0-beta.1', '0.2.1')).toBe(false)
    expect(isNewer('latest', '0.2.1')).toBe(false)
    expect(isNewer('0.3.0', 'dev')).toBe(false)
  })
})

describe('findUpdate', () => {
  it('offers a newer release with the installable archive for this machine', () => {
    expect(findUpdate(release(), '0.2.1', 'arm64')).toEqual({
      version: '0.3.0',
      notesUrl: 'https://github.com/gyedongjeon/sos-my-language/releases/tag/v0.3.0',
      archive: { url: `${DOWNLOADS}/v0.3.0/SOS.My.Language-0.3.0-arm64-mac.zip`, sha256: SHA, size: 1234 },
    })
  })

  it('offers nothing when the release is not newer', () => {
    expect(findUpdate(release(), '0.3.0', 'arm64')).toBeNull()
    expect(findUpdate(release(), '0.4.0', 'arm64')).toBeNull()
  })

  it('offers nothing for drafts, pre-releases, or an unexpected reply', () => {
    expect(findUpdate(release({ draft: true }), '0.2.1', 'arm64')).toBeNull()
    expect(findUpdate(release({ prerelease: true }), '0.2.1', 'arm64')).toBeNull()
    expect(findUpdate(release({ tag_name: 'nightly' }), '0.2.1', 'arm64')).toBeNull()
    expect(findUpdate({ message: 'API rate limit exceeded' }, '0.2.1', 'arm64')).toBeNull()
    expect(findUpdate(null, '0.2.1', 'arm64')).toBeNull()
  })

  it('reports the new version without an archive when none can be installed automatically', () => {
    const noArchive = { version: '0.3.0', notesUrl: release().html_url, archive: null }
    // Built for another kind of processor.
    expect(findUpdate(release(), '0.2.1', 'x64')).toEqual(noArchive)
    // No checksum to verify the download against.
    const [dmg, zip] = release().assets
    expect(findUpdate(release({}, [dmg, { ...zip, digest: null }]), '0.2.1', 'arm64')).toEqual(noArchive)
    // Still uploading.
    expect(findUpdate(release({}, [dmg, { ...zip, state: 'starter' }]), '0.2.1', 'arm64')).toEqual(noArchive)
  })

  it('never offers a download from outside the project releases', () => {
    const [dmg, zip] = release().assets
    const elsewhere = { ...zip, browser_download_url: 'https://example.com/SOS.My.Language-0.3.0-arm64-mac.zip' }
    expect(findUpdate(release({}, [dmg, elsewhere]), '0.2.1', 'arm64')?.archive).toBeNull()
    const lookalike = { ...zip, browser_download_url: `${DOWNLOADS}.evil.example/v0.3.0/x-arm64-mac.zip` }
    expect(findUpdate(release({}, [dmg, lookalike]), '0.2.1', 'arm64')?.archive).toBeNull()
  })

  it('links only to the project release page', () => {
    expect(findUpdate(release({ html_url: 'https://example.com/phish' }), '0.2.1', 'arm64')?.notesUrl).toBe(
      'https://github.com/gyedongjeon/sos-my-language/releases/latest',
    )
  })
})

describe('bundlePath', () => {
  it('is the .app folder that contains the running program', () => {
    expect(bundlePath('/Applications/SOS My Language.app/Contents/MacOS/SOS My Language')).toBe('/Applications/SOS My Language.app')
  })

  it('is null when the program is not inside an app bundle', () => {
    expect(bundlePath('/repo/desktop/node_modules/electron/dist/electron')).toBeNull()
  })
})

describe('replaceBlocker', () => {
  const installed = { packaged: true, platform: 'darwin' as NodeJS.Platform, bundle: '/Applications/SOS My Language.app', writable: () => true }

  it('allows replacing an installed app', () => {
    expect(replaceBlocker(installed)).toBeNull()
  })

  it('explains why the app cannot replace itself', () => {
    expect(replaceBlocker({ ...installed, packaged: false })).toMatch(/checkout/)
    expect(replaceBlocker({ ...installed, platform: 'win32' })).toMatch(/installer/)
    expect(replaceBlocker({ ...installed, bundle: null })).toMatch(/app bundle/)
    // macOS runs a quarantined app that was never moved from a random read-only location.
    expect(replaceBlocker({ ...installed, bundle: '/private/var/folders/x/AppTranslocation/1234/d/SOS My Language.app' })).toMatch(/Applications/)
    expect(replaceBlocker({ ...installed, bundle: '/Volumes/SOS My Language 0.2.1-arm64/SOS My Language.app' })).toMatch(/Applications/)
    expect(replaceBlocker({ ...installed, writable: () => false })).toMatch(/permission/)
  })
})

describe('with real files', () => {
  let dir: string
  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'sos-update-test-'))
  })
  afterEach(() => rmSync(dir, { recursive: true, force: true }))

  describe('download', () => {
    const body = Buffer.from('new version')
    const sha256 = createHash('sha256').update(body).digest('hex')
    const serve = async () => new Response(body)

    it('saves the archive when its checksum matches, reporting progress', async () => {
      const dest = join(dir, 'update.zip')
      const progress: number[] = []
      await download({ url: 'https://x/update.zip', sha256, size: body.length }, dest, serve, (done) => progress.push(done))
      expect(readFileSync(dest)).toEqual(body)
      expect(progress.at(-1)).toBe(1)
    })

    it('refuses and removes a download whose checksum differs', async () => {
      const dest = join(dir, 'update.zip')
      await expect(download({ url: 'https://x/update.zip', sha256: SHA, size: body.length }, dest, serve)).rejects.toThrow(/checksum/)
      expect(existsSync(dest)).toBe(false)
    })

    it('reports a failed request', async () => {
      const dest = join(dir, 'update.zip')
      const notFound = async () => new Response('missing', { status: 404 })
      await expect(download({ url: 'https://x/update.zip', sha256, size: 1 }, dest, notFound)).rejects.toThrow(/404/)
      expect(existsSync(dest)).toBe(false)
    })
  })

  describe('SWAP_SCRIPT', () => {
    // Runs the real script on stand-in "app" folders; `true` stands in for reopening the app.
    const swap = (pid: number, env: Record<string, string> = {}) => {
      const [current, next, backup] = ['Current.app', 'Next.app', 'Backup.app'].map((name) => join(dir, name))
      const result = spawnSync('/bin/bash', ['-c', SWAP_SCRIPT, 'swap', String(pid), current, next, backup, 'true'], {
        env: { ...process.env, ...env },
      })
      return { current, next, backup, status: result.status }
    }
    const app = (name: string, version: string) => {
      mkdirSync(join(dir, name))
      writeFileSync(join(dir, name, 'version'), version)
    }
    // The id of a process that has already ended.
    const endedPid = () => spawnSync('/usr/bin/true').pid as number

    it('puts the new version in place of the old one once the app has quit', () => {
      app('Current.app', 'old')
      app('Next.app', 'new')
      const { current, next, backup, status } = swap(endedPid())
      expect(status).toBe(0)
      expect(readFileSync(join(current, 'version'), 'utf8')).toBe('new')
      expect(existsSync(next)).toBe(false)
      expect(existsSync(backup)).toBe(false)
    })

    it('keeps the old version when the new one cannot be moved in', () => {
      app('Current.app', 'old')
      const { current, backup } = swap(endedPid())
      expect(readFileSync(join(current, 'version'), 'utf8')).toBe('old')
      expect(existsSync(backup)).toBe(false)
    })

    it('changes nothing while the app is still running', () => {
      app('Current.app', 'old')
      app('Next.app', 'new')
      const { current, next, status } = swap(process.pid, { SWAP_WAIT_TRIES: '1' })
      expect(status).not.toBe(0)
      expect(readFileSync(join(current, 'version'), 'utf8')).toBe('old')
      expect(readFileSync(join(next, 'version'), 'utf8')).toBe('new')
    })
  })
})
