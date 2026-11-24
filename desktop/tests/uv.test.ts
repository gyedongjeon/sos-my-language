import { describe, expect, it } from 'vitest'
import { findUv } from '../src/uv'

// A file system that contains only the given files.
const lookup = (files: string[], overrides: Partial<Parameters<typeof findUv>[0]> = {}) => ({
  path: '/usr/bin:/opt/tools',
  home: '/Users/me',
  platform: 'darwin' as NodeJS.Platform,
  bundledDir: null,
  exists: (file: string) => files.includes(file),
  ...overrides,
})

describe('findUv', () => {
  it('uses the uv bundled with the app before any installed one', () => {
    const files = ['/App/Resources/uv/uv', '/opt/tools/uv']
    expect(findUv(lookup(files, { bundledDir: '/App/Resources/uv' }))).toBe('/App/Resources/uv/uv')
  })

  it('falls back to an installed uv when the bundled one is missing', () => {
    expect(findUv(lookup(['/opt/tools/uv'], { bundledDir: '/App/Resources/uv' }))).toBe('/opt/tools/uv')
  })

  it('finds uv on the PATH when nothing is bundled', () => {
    expect(findUv(lookup(['/opt/tools/uv', '/Users/me/.local/bin/uv']))).toBe('/opt/tools/uv')
  })

  it('looks where uv is usually installed, since apps opened from Finder get no shell PATH', () => {
    expect(findUv(lookup(['/Users/me/.local/bin/uv'], { path: undefined }))).toBe('/Users/me/.local/bin/uv')
    expect(findUv(lookup(['/opt/homebrew/bin/uv'], { path: '' }))).toBe('/opt/homebrew/bin/uv')
  })

  it('returns null when uv is nowhere', () => {
    expect(findUv(lookup([]))).toBeNull()
  })

  it('is named uv.exe on Windows', () => {
    const files = ['/App/Resources/uv/uv.exe']
    expect(findUv(lookup(files, { platform: 'win32', bundledDir: '/App/Resources/uv' }))).toBe('/App/Resources/uv/uv.exe')
    expect(findUv(lookup(['/App/Resources/uv/uv'], { platform: 'win32', bundledDir: '/App/Resources/uv' }))).toBeNull()
  })
})
