// Finding the `uv` program that runs the Python backend.
import { delimiter, join } from 'node:path'

export interface UvLookup {
  /** The PATH environment variable. */
  path: string | undefined
  home: string
  platform: NodeJS.Platform
  exists: (file: string) => boolean
  /** Folder holding the uv shipped inside the packaged app; null when running from a checkout. */
  bundledDir: string | null
}

/**
 * The uv shipped with the app comes first, so a user needs nothing installed. Otherwise an
 * installed one is used; apps opened from Finder do not get the shell's PATH, so the usual
 * install folders are searched too.
 */
export function findUv({ path, home, platform, exists, bundledDir }: UvLookup): string | null {
  const name = platform === 'win32' ? 'uv.exe' : 'uv'
  const folders = [
    ...(bundledDir ? [bundledDir] : []),
    ...(path ?? '').split(delimiter),
    join(home, '.local', 'bin'),
    join(home, '.cargo', 'bin'),
    '/opt/homebrew/bin',
    '/usr/local/bin',
  ]
  return folders.map((folder) => join(folder, name)).find(exists) ?? null
}
