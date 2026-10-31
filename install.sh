#!/usr/bin/env bash
# Usage: ./install.sh [config.yml] [extra ansible-playbook options]
#
# If a bundle/ folder is here (made by build-bundle.sh), it installs offline:
# Ansible, packages and images all come from the bundle.
set -euo pipefail

config="${1:-config.yml}"
[ "$#" -gt 0 ] && shift
if [ ! -f "$config" ]; then
  echo "error: $config not found (cp config.example.yml config.yml)" >&2
  exit 1
fi
# Full path, so it still works after we change folder below.
ANNIBLE_CONFIG="$(cd "$(dirname "$config")" && pwd)/$(basename "$config")"
export ANNIBLE_CONFIG

cd "$(dirname "$0")"
offline=false
[ -f bundle/info.yml ] && offline=true

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
exec ansible-playbook site.yml "$@"
