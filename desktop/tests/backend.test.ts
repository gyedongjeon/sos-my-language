import { describe, expect, it } from 'vitest'
import { backendLaunch, microphoneSettings, startupProgress, stopCommand } from '../src/backend'

const options = {
  project: '/App/Resources/backend',
  frontend: '/App/Resources/frontend',
  userData: '/Users/me/Library/Application Support/SOS My Language' as string | null,
  port: 51234,
  env: { PATH: '/usr/bin', HOME: '/Users/me' },
}

describe('backendLaunch', () => {
  it('runs the server through uv on the given port', () => {
    const { args } = backendLaunch(options)
    expect(args.slice(0, 3)).toEqual(['run', '--project', '/App/Resources/backend'])
    expect(args.slice(-6)).toEqual(['uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '51234'])
  })

  it('keeps the caller environment and tells the backend where the built frontend is', () => {
    const { env } = backendLaunch(options)
    expect(env.PATH).toBe('/usr/bin')
    expect(env.SOS_MY_LANGUAGE_FRONTEND_DIST).toBe('/App/Resources/frontend')
  })

  it('keeps compiled Python in the packaged app\'s folder, so later launches need not compile it again', () => {
    const { env } = backendLaunch(options)
    expect(env.PYTHONPYCACHEPREFIX).toBe('/Users/me/Library/Application Support/SOS My Language/pycache')
    // Compiled files are still written, but not into the app bundle, which must stay unchanged.
    expect(env.PYTHONDONTWRITEBYTECODE).toBeUndefined()
  })

  it('keeps the packaged app\'s data and Python packages in its own folder, without the test tools', () => {
    const { args, env } = backendLaunch(options)
    expect(env.SOS_MY_LANGUAGE_DATA_DIR).toBe('/Users/me/Library/Application Support/SOS My Language/data')
    expect(env.UV_PROJECT_ENVIRONMENT).toBe('/Users/me/Library/Application Support/SOS My Language/venv')
    expect(args).toContain('--frozen')
    expect(args).toContain('--no-dev')
  })

  it("keeps uv's downloads in the same folder, so removing that folder removes everything", () => {
    const { env } = backendLaunch(options)
    expect(env.UV_CACHE_DIR).toBe('/Users/me/Library/Application Support/SOS My Language/uv-cache')
    expect(env.UV_PYTHON_INSTALL_DIR).toBe('/Users/me/Library/Application Support/SOS My Language/python')
  })

  it('leaves the choice of Python to the project, which pins it for every way of running', () => {
    // backend/.python-version is shipped with the app; see tests/package.test.ts.
    expect(backendLaunch(options).args).not.toContain('--python')
  })

  it('leaves a checkout to its own defaults', () => {
    const { args, env } = backendLaunch({ ...options, userData: null })
    expect(env.SOS_MY_LANGUAGE_DATA_DIR).toBeUndefined()
    expect(env.UV_PROJECT_ENVIRONMENT).toBeUndefined()
    expect(env.UV_CACHE_DIR).toBeUndefined()
    expect(env.UV_PYTHON_INSTALL_DIR).toBeUndefined()
    expect(env.PYTHONPYCACHEPREFIX).toBeUndefined()
    expect(env.PYTHONDONTWRITEBYTECODE).toBe('1')
    expect(args).not.toContain('--frozen')
    expect(args).not.toContain('--no-dev')
    expect(args).not.toContain('--python')
  })
})

describe('backendLaunch with a Python shipped in the app', () => {
  const python = 'C:\\Programs\\sos\\resources\\python\\python.exe'

  it('runs on that Python and downloads none, so the first launch does not depend on that download', () => {
    const { env } = backendLaunch({ ...options, python })
    expect(env.UV_PYTHON).toBe(python)
    expect(env.UV_PYTHON_DOWNLOADS).toBe('never')
  })

  it('lets uv fetch the pinned Python where none is shipped', () => {
    const { env } = backendLaunch(options)
    expect(env.UV_PYTHON).toBeUndefined()
    expect(env.UV_PYTHON_DOWNLOADS).toBeUndefined()
  })
})

describe('stopCommand', () => {
  it('ends the whole process tree on Windows, where uv and the Python server are separate processes', () => {
    expect(stopCommand('win32', 4321)).toEqual({ command: 'taskkill', args: ['/pid', '4321', '/T', '/F'] })
  })

  it('needs no command elsewhere, where the process group is signalled', () => {
    expect(stopCommand('darwin', 4321)).toBeNull()
    expect(stopCommand('linux', 4321)).toBeNull()
  })
})

describe('startupProgress', () => {
  const python = 'Downloading cpython-3.14.10-windows-x86_64-none (download) (22.6MiB)\r\n'
  const gotPython = ' Downloaded cpython-3.14.10-windows-x86_64-none (download)\r\n'

  it('only says the app is starting when nothing has to be set up', () => {
    expect(startupProgress('')).toEqual({ label: 'Starting…', fraction: null })
    expect(startupProgress('INFO:     Started server process [1234]\n')).toEqual({ label: 'Starting…', fraction: null })
  })

  it('starts with Python, which is a small first part of the whole', () => {
    expect(startupProgress(python)).toEqual({ label: 'Downloading Python…', fraction: 0 })
    expect(startupProgress(python + gotPython)).toEqual({ label: 'Downloading packages…', fraction: 0.1 })
  })

  it('fills up by the size of the packages that have arrived', () => {
    const log =
      python +
      gotPython +
      'Downloading onnxruntime (100.0MiB)\nDownloading numpy (50.0MiB)\nDownloading tokenizers (512.0KiB)\n' +
      ' Downloaded numpy\n Downloaded openai\n'
    const { label, fraction } = startupProgress(log)
    expect(label).toBe('Downloading packages… 50 of 151 MB')
    // A third of the packages, which take the part between Python and installing.
    expect(fraction).toBeCloseTo(0.1 + 0.75 * (50 / 150.5), 3)
  })

  it('reads the colour codes a terminal would get', () => {
    const log = '\u001b[2mDownloading\u001b[0m numpy (10.0MiB)\n \u001b[2mDownloaded\u001b[0m numpy\n'
    expect(startupProgress(log).label).toBe('Downloading packages… 10 of 10 MB')
  })

  it('goes on to installing and then to starting', () => {
    const downloaded = 'Downloading numpy (10.0MiB)\n Downloaded numpy\nPrepared 84 packages in 1m 02s\n'
    expect(startupProgress(downloaded)).toEqual({ label: 'Installing packages…', fraction: 0.85 })
    expect(startupProgress(downloaded + 'Installed 84 packages in 12.3s\n')).toEqual({ label: 'Starting…', fraction: 0.95 })
  })

  it('counts a Python that was already there as done', () => {
    expect(startupProgress('Downloading numpy (10.0MiB)\n').fraction).toBe(0.1)
  })
})

describe('microphoneSettings', () => {
  it('is the page of the system settings where microphone access is allowed', () => {
    expect(microphoneSettings('win32')).toBe('ms-settings:privacy-microphone')
    expect(microphoneSettings('darwin')).toBe('x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone')
  })

  it('is not known on other systems', () => {
    expect(microphoneSettings('linux')).toBeNull()
  })
})
