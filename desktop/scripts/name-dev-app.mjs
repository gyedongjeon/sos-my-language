// `npm run dev` runs the Electron binary from node_modules, whose bundle is named "Electron", so
// the Dock and the menu bar would show that name. This gives that bundle the product name: the
// Dock labels an app by its bundle's file name, the menu bar by the name in its Info.plist.
// The packaged app does not need it: electron-builder names its bundle.
import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const { productName } = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'))
const electron = join(root, 'node_modules', 'electron')
const original = join(electron, 'dist', 'Electron.app')
const bundle = join(electron, 'dist', `${productName}.app`)

if (process.platform === 'darwin' && (existsSync(original) || existsSync(bundle))) {
  if (existsSync(original)) {
    renameSync(original, bundle)
    // Where the `electron` command looks for the binary it runs.
    writeFileSync(join(electron, 'path.txt'), `${productName}.app/Contents/MacOS/Electron`)
    console.log(`Named the development app "${productName}".`)
  }
  const plist = join(bundle, 'Contents', 'Info.plist')
  const read = (key) => execFileSync('/usr/bin/plutil', ['-extract', key, 'raw', plist], { encoding: 'utf8' }).trim()
  if (read('CFBundleName') !== productName || read('CFBundleDisplayName') !== productName) {
    for (const key of ['CFBundleName', 'CFBundleDisplayName']) {
      execFileSync('/usr/bin/plutil', ['-replace', key, '-string', productName, plist])
    }
    // Info.plist is covered by the bundle's ad-hoc signature, so sign it again.
    execFileSync('/usr/bin/codesign', ['--force', '--sign', '-', bundle])
  }
}
