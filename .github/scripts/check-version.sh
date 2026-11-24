#!/usr/bin/env bash
# Fails unless the given tag (e.g. v0.2.0) is the version written in all three packages.
set -euo pipefail

tag="${1:?usage: check-version.sh <tag>}"
expected="${tag#v}"
root="$(cd "$(dirname "$0")/../.." && pwd)"

json_version() { sed -n 's/^  "version": "\(.*\)",$/\1/p' "$1" | head -1; }
toml_version() { sed -n 's/^version = "\(.*\)"$/\1/p' "$1" | head -1; }

status=0
check() {
  if [ "$2" != "$expected" ]; then
    echo "::error::$1 is at version '$2', but the tag is $tag" >&2
    status=1
  fi
}
check backend/pyproject.toml "$(toml_version "$root/backend/pyproject.toml")"
check frontend/package.json "$(json_version "$root/frontend/package.json")"
check desktop/package.json "$(json_version "$root/desktop/package.json")"

[ "$status" -eq 0 ] && echo "All packages are at $expected."
exit "$status"
