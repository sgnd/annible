#!/usr/bin/env bash
# Build an offline bundle: everything the servers need, so they need no internet.
#
# Usage: ./build-bundle.sh <arch> [ubuntu version]
#   ./build-bundle.sh amd64          # Intel/AMD servers, Ubuntu 24.04
#   ./build-bundle.sh arm64 24.04    # ARM servers
#
# Run it on any machine with Docker and internet (also a Mac). It makes
# dist/annible-<ubuntu>-<arch>.tar.gz with this project plus a bundle/ folder:
#   bundle/debs.tar       apt packages (Docker, chrony, ufw, ...)
#   bundle/python/        Ansible and its Python packages
#   bundle/collections/   Ansible collections
#   bundle/images/        Docker images from versions.yml
#   bundle/info.yml       Ubuntu version and arch of the bundle
set -euo pipefail

arch="${1:-}"
ubuntu="${2:-24.04}"
if [ "$arch" != amd64 ] && [ "$arch" != arm64 ]; then
  echo "usage: $0 <amd64|arm64> [ubuntu version]" >&2
  exit 1
fi

cd "$(dirname "$0")"
rm -rf bundle
mkdir -p bundle/images dist

echo "== apt packages, Python packages and collections (in an Ubuntu $ubuntu $arch container)"
docker run --rm --platform "linux/$arch" \
  -v "$PWD:/src:ro" -v "$PWD/bundle:/out" \
  "ubuntu:$ubuntu" bash /src/scripts/bundle-inside.sh

echo "== Docker images"
# bundle-inside.sh wrote one line per image: name repo tag digest
while read -r name repo tag digest; do
  echo "- $name"
  docker pull -q --platform "linux/$arch" "$repo@$digest" >/dev/null
  docker tag "$repo@$digest" "$repo:$tag"
  docker save --platform "linux/$arch" "$repo:$tag" | gzip > "bundle/images/$name.tar.gz"
done < bundle/images.txt

echo "== Pack"
file="dist/annible-$ubuntu-$arch.tar.gz"
rm -rf dist/annible
mkdir dist/annible
# --no-xattrs and COPYFILE_DISABLE: do not add macOS file attributes (Linux tar warns about them).
export COPYFILE_DISABLE=1
tar --no-xattrs -cf - --exclude ./.git --exclude ./.venv --exclude ./.collections --exclude ./state \
  --exclude ./dist --exclude ./config.yml . | tar -C dist/annible -xf -
tar --no-xattrs -C dist -czf "$file" annible
rm -rf dist/annible

echo "Done: $file ($(du -h "$file" | cut -f1))"
echo "Copy it to the first manager, then: tar -xzf $(basename "$file") && cd annible && ./install.sh"
