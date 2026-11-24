import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const config = JSON.parse(readFileSync(join(__dirname, '..', 'package.json'), 'utf8'))

describe('the packaged backend', () => {
  it('ships the Python version pin, so uv installs the Python the tests ran on', () => {
    const backend = config.build.extraResources.find((entry: { to: string }) => entry.to === 'backend')
    expect(backend.filter).toContain('.python-version')
  })
})

describe('the Windows installer', () => {
  it('is an installer for 64-bit Windows', () => {
    expect(config.build.win.target).toEqual([{ target: 'nsis', arch: ['x64'] }])
  })

  it('ships uv under the name it has on each platform', () => {
    const uv = config.build.extraResources.find((entry: { to: string }) => entry.to === 'uv')
    expect(uv.filter).toEqual(expect.arrayContaining(['uv', 'uv.exe']))
  })

  it('ships Python itself, so the first launch does not have to download it', () => {
    expect(config.build.win.extraResources).toEqual([{ from: 'vendor/python', to: 'python' }])
    expect(config.scripts.dist).toContain('npm run python')
  })

  it('installs for the current user, without asking for administrator rights', () => {
    expect(config.build.nsis.perMachine).toBe(false)
  })
})
