#!/usr/bin/env bash
# Keep state/ (passwords, keys, summary) encrypted on disk, as state.age.
#
# Turn it on once, on the machine that runs the installer:
#   mkdir -p ~/.config/ansibro && age-keygen -o ~/.config/ansibro/age.key
# Keep a copy of that key somewhere safe (a password manager): without it state.age cannot be opened.
#
# install.sh opens state.age before it runs and closes it again at the end. By hand:
#   scripts/state.sh open     state.age -> state/ (to read a password)
#   scripts/state.sh close    state/ -> state.age
# Another key file: ANSIBRO_KEY=/path/to/age.key scripts/state.sh open
set -euo pipefail
cd "$(dirname "$0")/.."

# HOME is not set when this runs from a service or cron; ~ then comes from the user list.
home="${HOME:-$(cd ~ && pwd)}"
key="${ANSIBRO_KEY:-$home/.config/ansibro/age.key}"

# Nothing to do when encryption is off (no key and no state.age).
if [ ! -f "$key" ] && [ ! -f state.age ]; then
  exit 0
fi
if ! command -v age >/dev/null; then
  echo "error: state is encrypted with age, but age is not installed (brew install age, or sudo apt install age)" >&2
  exit 1
fi
if [ ! -f "$key" ]; then
  echo "error: state.age is encrypted, but the key $key is missing (or set ANSIBRO_KEY)" >&2
  exit 1
fi

case "${1:-}" in
  open)
    [ -f state.age ] || exit 0
    if [ -d state ]; then
      echo "error: both state/ and state.age are here. Do not delete either: they hold your passwords." >&2
      echo "  Move one of them to a backup folder, then run this again." >&2
      exit 1
    fi
    age -d -i "$key" state.age | tar -xf -
    rm state.age
    ;;
  close)
    [ -d state ] || exit 0
    tar -cf - state | age -e -i "$key" -o state.age.new
    mv state.age.new state.age
    rm -rf state
    ;;
  *)
    echo "usage: scripts/state.sh open|close" >&2
    exit 1
    ;;
esac
