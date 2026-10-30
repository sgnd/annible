#!/usr/bin/env bash
# Usage: ./install.sh [config.yml] [extra ansible-playbook options]
set -euo pipefail

config="${1:-config.yml}"
[ "$#" -gt 0 ] && shift
if [ ! -f "$config" ]; then
  echo "error: $config not found (cp config.example.yml config.yml)" >&2
  exit 1
fi
# Full path, so it still works after we change folder below.
SWARM_CONFIG="$(cd "$(dirname "$config")" && pwd)/$(basename "$config")"
export SWARM_CONFIG

cd "$(dirname "$0")"

# Install Ansible in .venv. A copy of requirements.txt in .venv shows what is installed,
# so this only runs again when requirements.txt changes.
venv=.venv
if ! cmp -s requirements.txt "$venv/requirements.txt"; then
  if ! python3 -m venv "$venv" 2>/dev/null; then
    if command -v apt-get >/dev/null; then
      sudo apt-get update -qq
      sudo apt-get install -y python3-venv
      python3 -m venv "$venv"
    else
      echo "error: python3 with venv support is required" >&2
      exit 1
    fi
  fi
  "$venv/bin/pip" install --quiet -r requirements.txt
  cp requirements.txt "$venv/requirements.txt"
fi

"$venv/bin/ansible-galaxy" collection install -r requirements.yml >/dev/null

export PATH="$PWD/$venv/bin:$PATH"
exec ansible-playbook site.yml "$@"
