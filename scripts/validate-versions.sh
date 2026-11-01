#!/usr/bin/env bash
# Checks that every version pinned in versions.yml still exists:
#   - each Docker image digest, with an amd64 and an arm64 build
#   - each Docker apt package, for Ubuntu 24.04 (noble) and 26.04 (resolute), on amd64 and arm64
# Needs: yq, docker (buildx), curl.
set -euo pipefail
cd "$(dirname "$0")/.."

failed=0

echo "== Docker images"
for name in $(yq '.images | keys | .[]' versions.yml); do
  repo=$(yq ".images[\"$name\"].repo" versions.yml)
  digest=$(yq ".images[\"$name\"].digest" versions.yml)
  platforms=$(docker buildx imagetools inspect "$repo@$digest" 2>/dev/null | grep 'Platform:' || true)
  for arch in amd64 arm64; do
    if ! grep -q "linux/$arch" <<< "$platforms"; then
      echo "MISSING $name ($repo@$digest) for $arch"
      failed=1
    fi
  done
  echo "ok $name"
done

echo "== Docker apt packages"
for target in noble/amd64 noble/arm64 resolute/amd64 resolute/arm64; do
  ubuntu=${target%/*}
  arch=${target#*/}
  # One line per package: "name version"
  available=$(curl -fsSL "https://download.docker.com/linux/ubuntu/dists/$ubuntu/stable/binary-$arch/Packages" \
    | awk '/^Package: /{p=$2} /^Version: /{print p, $2}')
  for spec in $(yq '.docker_packages[]' versions.yml); do
    name=${spec%%=*}
    version=${spec#*=}
    version=${version%\*}
    if ! grep -q "^$name $version" <<< "$available"; then
      echo "MISSING $name $version for $ubuntu $arch"
      failed=1
    fi
  done
  echo "ok $ubuntu $arch"
done

echo "== NVIDIA Container Toolkit"
version=$(yq '.nvidia_container_toolkit' versions.yml)
for arch in amd64 arm64; do
  if curl -fsSL "https://nvidia.github.io/libnvidia-container/stable/deb/$arch/Packages" \
      | awk '/^Package: /{p=$2} /^Version: /{print p, $2}' | grep -q "^nvidia-container-toolkit $version$"; then
    echo "ok $arch"
  else
    echo "MISSING nvidia-container-toolkit $version for $arch"
    failed=1
  fi
done

exit $failed
