#!/usr/bin/env bash
# Usage: ./install.sh [config.yml] [extra ansible-playbook options]
#   ./install.sh                     uses config.yml
#   ./install.sh prod.yml -v         another config file, plus an ansible-playbook option
#
# If a bundle/ folder is here (made by build-bundle.sh), it installs offline:
# Ansible, packages and images all come from the bundle.
set -euo pipefail

# The first argument is the config file, unless it is an option like -v.
config=config.yml
if [ "$#" -gt 0 ] && [ "${1#-}" = "$1" ]; then
  config="$1"
  shift
fi
if [ ! -f "$config" ]; then
  echo "error: $config not found (cp config.example.yml config.yml)" >&2
  exit 1
fi
# Full path, so it still works after we change folder below.
ANSIBRO_CONFIG="$(cd "$(dirname "$config")" && pwd)/$(basename "$config")"
export ANSIBRO_CONFIG

cd "$(dirname "$0")"

# Ansible needs Python 3.12 or newer.
if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 12))' 2>/dev/null; then
  echo "error: Python 3.12 or newer is needed, found: $(python3 --version 2>&1)" >&2
  echo "  On a Mac: brew install python@3.12 (or newer), then run ./install.sh again." >&2
  exit 1
fi

offline=false
[ -f bundle/info.yml ] && offline=true

# Offline: this machine must match the bundle (its packages are for one Ubuntu version and CPU).
if $offline; then
  bundle_ubuntu=$(sed -n 's/^ubuntu: "\(.*\)"/\1/p' bundle/info.yml)
  bundle_arch=$(sed -n 's/^arch: //p' bundle/info.yml)
  here_ubuntu=$(sed -n 's/^VERSION_ID="\(.*\)"/\1/p' /etc/os-release 2>/dev/null || true)
  here_arch=$(dpkg --print-architecture 2>/dev/null || true)
  if [ "$here_ubuntu" != "$bundle_ubuntu" ] || [ "$here_arch" != "$bundle_arch" ]; then
    echo "error: this bundle is for Ubuntu $bundle_ubuntu $bundle_arch, this machine is ${here_ubuntu:-not Ubuntu} ${here_arch}." >&2
    echo "  Run the offline install on the first manager, or build a matching bundle:" >&2
    echo "  ./build-bundle.sh <amd64|arm64> <ubuntu version>" >&2
    exit 1
  fi
fi

# Install python3-venv with apt, from the internet or from the bundle.
install_venv_package() {
  if ! command -v apt-get >/dev/null; then
    echo "error: python3 with venv support is required" >&2
    exit 1
  fi
  if $offline; then
    mkdir -p bundle/debs bundle/apt/lists/partial bundle/apt/sources.d
    tar -C bundle/debs -xf bundle/debs.tar
    echo "deb [trusted=yes] file:$PWD/bundle/debs ./" > bundle/apt/sources.list
    cat > bundle/apt/apt.conf <<EOF
Dir::Etc::SourceList "$PWD/bundle/apt/sources.list";
Dir::Etc::SourceParts "$PWD/bundle/apt/sources.d";
Dir::State::Lists "$PWD/bundle/apt/lists";
EOF
    export APT_CONFIG="$PWD/bundle/apt/apt.conf"
  fi
  sudo --preserve-env=APT_CONFIG apt-get update -qq
  sudo --preserve-env=APT_CONFIG apt-get install -y -qq python3-venv
}

# Install Ansible in .venv. A copy of requirements.txt in .venv shows what is installed,
# so this only runs again when requirements.txt changes.
venv=.venv
if ! cmp -s requirements.txt "$venv/requirements.txt"; then
  python3 -m venv "$venv" 2>/dev/null || { install_venv_package && python3 -m venv "$venv"; }
  if $offline; then
    "$venv/bin/pip" install --quiet --no-index --find-links bundle/python -r requirements.txt
  else
    "$venv/bin/pip" install --quiet -r requirements.txt
  fi
  cp requirements.txt "$venv/requirements.txt"
fi

if $offline; then
  (cd bundle/collections && "../../$venv/bin/ansible-galaxy" collection install -r requirements.yml -p ../../.collections >/dev/null)
else
  "$venv/bin/ansible-galaxy" collection install -r requirements.yml >/dev/null
fi

export PATH="$PWD/$venv/bin:$PATH"

# Check config.yml first, so a mistake stops here with a clear message.
if ! "$venv/bin/python" inventory.py --list >/dev/null; then
  exit 1
fi

# state/ holds the passwords. If it is kept encrypted (see scripts/state.sh), open it now
# and close it again when the install ends, also when it fails.
scripts/state.sh open
trap 'scripts/state.sh close' EXIT

ansible-playbook site.yml "$@"
