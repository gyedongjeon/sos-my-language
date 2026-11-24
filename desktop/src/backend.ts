// How the Python backend is started: the arguments for uv and the environment it runs in.
import { join } from 'node:path'

export interface BackendOptions {
  /** The folder with the backend's pyproject.toml. */
  project: string
  /** The built frontend the backend serves. */
  frontend: string
  /** The packaged app's own folder in the user's profile; null when running from a checkout. */
  userData: string | null
  port: number
  env: NodeJS.ProcessEnv
  /** The Python shipped inside the app, where there is one; otherwise uv downloads it. */
  python?: string | null
}

export function backendLaunch({ project, frontend, userData, port, env, python }: BackendOptions) {
  const launchEnv: NodeJS.ProcessEnv = {
    ...env,
    SOS_MY_LANGUAGE_FRONTEND_DIST: frontend,
  }
  if (python) {
    // Shipped with the Windows app: on a first trial there, downloading Python stalled every time.
    launchEnv.UV_PYTHON = python
    launchEnv.UV_PYTHON_DOWNLOADS = 'never'
  }
  const args = ['run', '--project', project]
  if (userData) {
    // The app bundle is read-only, so the packaged app keeps its files in the user's profile.
    launchEnv.SOS_MY_LANGUAGE_DATA_DIR = join(userData, 'data')
    launchEnv.UV_PROJECT_ENVIRONMENT = join(userData, 'venv')
    // uv's download cache and the Python it installs would otherwise go to shared folders in
    // the home folder; here, removing the app's folder removes everything the app put on disk.
    launchEnv.UV_CACHE_DIR = join(userData, 'uv-cache')
    launchEnv.UV_PYTHON_INSTALL_DIR = join(userData, 'python')
    // Python's compiled files go here too, not into the app bundle, which must stay unchanged.
    // Without them every launch compiles the packages again, which takes seconds.
    launchEnv.PYTHONPYCACHEPREFIX = join(userData, 'pycache')
    // The packaged app needs only what runs the server, not the test tools.
    args.push('--frozen', '--no-dev')
    // uv installs the Python named in the project's .python-version, which ships with the app.
  } else {
    // Keep a checkout free of compiled files.
    launchEnv.PYTHONDONTWRITEBYTECODE = '1'
  }
  args.push('uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(port))
  return { args, env: launchEnv }
}

/**
 * The command that stops the backend, where one is needed. On Windows uv starts the Python
 * server as a process of its own and ending uv leaves it running, so the whole tree is ended.
 * Elsewhere the backend runs in its own process group, which is signalled instead.
 */
export function stopCommand(platform: NodeJS.Platform, pid: number): { command: string; args: string[] } | null {
  return platform === 'win32' ? { command: 'taskkill', args: ['/pid', String(pid), '/T', '/F'] } : null
}

// Colour and cursor codes that a tool writes for a terminal.
const TERMINAL_CODES = /\u001b\[[0-9;?]*[A-Za-z]/g

export interface Progress {
  /** What the first launch is doing, in words for the waiting screen. */
  label: string
  /** How far along it is, from 0 to 1; null when there is nothing to measure. */
  fraction: number | null
}

// The parts of the first launch, as shares of the whole: Python, then the packages, then
// installing them. The rest is the server starting.
const PYTHON_SHARE = 0.1
const PACKAGES_SHARE = 0.75
const INSTALLED = 0.95

const MEGABYTES: Record<string, number> = { KiB: 1 / 1024, MiB: 1, GiB: 1024 }

/**
 * How far the first launch has come, read from what uv has written so far. uv names each large
 * download with its size when it starts and again when it ends, so the bar follows the size of
 * what has arrived. Small packages are not named, which makes this an estimate.
 */
export function startupProgress(log: string): Progress {
  const lines = log
    .replace(TERMINAL_CODES, '')
    .split(/[\r\n]+/)
    .map((line) => line.trim())
  const sizes = new Map<string, number>()
  const arrived = new Set<string>()
  let python: 'none' | 'downloading' | 'done' = 'none'
  let prepared = false
  let installed = false
  for (const line of lines) {
    const started = /^Downloading (\S+)(?: \(download\))? \(([\d.]+)\s*(KiB|MiB|GiB)\)/.exec(line)
    const ended = /^Downloaded (\S+)/.exec(line)
    const name = (started ?? ended)?.[1]
    if (name?.startsWith('cpython-')) python = started ? 'downloading' : 'done'
    else if (started) sizes.set(started[1], Number(started[2]) * MEGABYTES[started[3]])
    else if (ended) arrived.add(ended[1])
    else if (/^Prepared \d+ package/.test(line)) prepared = true
    else if (/^Installed \d+ package/.test(line)) installed = true
  }

  if (installed) return { label: 'Starting…', fraction: INSTALLED }
  if (prepared) return { label: 'Installing packages…', fraction: PYTHON_SHARE + PACKAGES_SHARE }
  if (python === 'downloading') return { label: 'Downloading Python…', fraction: 0 }
  if (sizes.size === 0) {
    return python === 'done' ? { label: 'Downloading packages…', fraction: PYTHON_SHARE } : { label: 'Starting…', fraction: null }
  }
  let total = 0
  let done = 0
  for (const [name, size] of sizes) {
    total += size
    if (arrived.has(name)) done += size
  }
  return {
    label: `Downloading packages… ${Math.round(done)} of ${Math.round(total)} MB`,
    fraction: PYTHON_SHARE + PACKAGES_SHARE * (done / total),
  }
}

/** The page of the system settings where microphone access is allowed, where there is one to open. */
export function microphoneSettings(platform: NodeJS.Platform): string | null {
  if (platform === 'win32') return 'ms-settings:privacy-microphone'
  if (platform === 'darwin') return 'x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone'
  return null
}
