#!/usr/bin/env bash
# Build an offline bundle: everything the servers need, so they need no internet.
#
# Usage: ./build-bundle.sh <arch> [ubuntu version]
#   ./build-bundle.sh amd64          # Intel/AMD servers, Ubuntu 24.04
#   ./build-bundle.sh arm64 26.04    # ARM servers, Ubuntu 26.04
#
# Run it on any machine with Docker and internet (also a Mac). It makes
# dist/ansibro-<ubuntu>-<arch>.tar.gz: a copy of this project plus a bundle/ folder:
#   bundle/debs.tar       apt packages (Docker, chrony, ufw, ...)
#   bundle/python/        Ansible and its Python packages
#   bundle/collections/   Ansible collections
#   bundle/images/        Docker images from versions.yml (list in bundle/images.txt)
#   bundle/info.yml       Ubuntu version and arch of the bundle
# Your project folder is not changed: the work happens in dist/.
set -euo pipefail

arch="${1:-}"
ubuntu="${2:-24.04}"
if [ "$arch" != amd64 ] && [ "$arch" != arm64 ]; then
  echo "usage: $0 <amd64|arm64> [24.04|26.04]" >&2
  exit 1
fi
if [ "$ubuntu" != 24.04 ] && [ "$ubuntu" != 26.04 ]; then
  echo "error: Ubuntu $ubuntu is not supported, use 24.04 or 26.04" >&2
  exit 1
fi

cd "$(dirname "$0")"
file="dist/ansibro-$ubuntu-$arch.tar.gz"
root="dist/build-$ubuntu-$arch"   # one work folder per bundle, so two builds can run at once
work="$root/ansibro"              # the folder that goes into the tar file
bundle="$work/bundle"

echo "== Copy the project"
# Only the files git knows about, so your own configs, keys and passwords never go in.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "error: run this in a git clone of ansibro (it copies only the files git tracks)" >&2
  exit 1
fi
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "warning: you have changes that are not committed; the bundle has the committed files only." >&2
fi
rm -rf "$root"
mkdir -p "$bundle/images"
# --no-xattrs and COPYFILE_DISABLE: do not add macOS file attributes (Linux tar warns about them).
export COPYFILE_DISABLE=1
git archive HEAD | tar -C "$work" -xf -

echo "== apt packages, Python packages and collections (in an Ubuntu $ubuntu $arch container)"
# OWNER: the container gives the files back to you (on Linux it would leave them owned by root).
docker run --rm --platform "linux/$arch" -e OWNER="$(id -u):$(id -g)" \
  -v "$PWD:/src:ro" -v "$PWD/$bundle:/out" \
  "ubuntu:$ubuntu" bash /src/scripts/bundle-inside.sh

echo "== Docker images"
# bundle-inside.sh wrote one line per image: name repo tag digest
while read -r name repo tag digest; do
  echo "- $name"
  # Try 3 times: a slow or unstable network often fails once.
  for try in 1 2 3; do
    if docker pull -q --platform "linux/$arch" "$repo@$digest" >/dev/null; then break; fi
    if [ "$try" = 3 ]; then exit 1; fi
    echo "  download failed, trying again in 15 seconds"
    sleep 15
  done
  docker tag "$repo@$digest" "$repo:$tag"
  docker save --platform "linux/$arch" "$repo:$tag" | gzip > "$bundle/images/$name.tar.gz"
done < "$bundle/images.txt"

echo "== Pack"
tar --no-xattrs -C "$root" -czf "$file" ansibro
rm -rf "$root"

echo "Done: $file ($(du -h "$file" | cut -f1))"
echo "Next: copy it and your SSH key to the first manager, then:"
echo "  tar -xzf $(basename "$file") && cd ansibro"
echo "  cp config.example.yml config.yml   # set tls: selfsigned, ssh.key, servers, apps"
echo "  ./install.sh"
