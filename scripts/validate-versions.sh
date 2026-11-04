#!/usr/bin/env bash
# Checks that every version pinned in versions.yml still exists:
#   - each Docker image digest, with an amd64 build, and that its tag still points to that digest
#   - the Ubuntu image digests that build-bundle.sh uses
#   - each Docker apt package, for Ubuntu 24.04 (noble) and 26.04 (resolute), on amd64
# Needs: yq, docker (buildx), curl.
set -euo pipefail
cd "$(dirname "$0")/.."

failed=0

echo "== Docker images"
for name in $(yq '.images | keys | .[]' versions.yml); do
  repo=$(yq ".images[\"$name\"].repo" versions.yml)
  tag=$(yq ".images[\"$name\"].tag" versions.yml)
  digest=$(yq ".images[\"$name\"].digest" versions.yml)
  platforms=$(docker buildx imagetools inspect "$repo@$digest" 2>/dev/null | grep 'Platform:' || true)
  # The digest the tag points to now (the first "Digest:" line).
  tag_digest=$(docker buildx imagetools inspect "$repo:$tag" 2>/dev/null | awk '/^Digest:/ {print $2; exit}' || true)
  if ! grep -q "linux/amd64" <<< "$platforms"; then
    echo "MISSING $name ($repo@$digest) for amd64"
    failed=1
  elif [ "$tag_digest" != "$digest" ]; then
    echo "WRONG $name: $repo:$tag points to ${tag_digest:-nothing}, not $digest"
    failed=1
  else
    echo "ok $name"
  fi
done

echo "== Ubuntu images (build-bundle.sh builds the bundle in them)"
for version in $(yq '.ubuntu_images | keys | .[]' versions.yml); do
  digest=$(yq ".ubuntu_images[\"$version\"]" versions.yml)
  # Only the digest: the tag gets a new build every few weeks.
  if docker buildx imagetools inspect "docker.io/library/ubuntu@$digest" 2>/dev/null | grep -q 'linux/amd64'; then
    echo "ok ubuntu $version"
  else
    echo "MISSING ubuntu $version (docker.io/library/ubuntu@$digest) for amd64"
    failed=1
  fi
done

echo "== Docker apt packages"
for ubuntu in noble resolute; do
  # One line per package: "name version"
  available=$(curl -fsSL "https://download.docker.com/linux/ubuntu/dists/$ubuntu/stable/binary-amd64/Packages" \
    | awk '/^Package: /{p=$2} /^Version: /{print p, $2}')
  for spec in $(yq '.docker_packages[]' versions.yml); do
    name=${spec%%=*}
    version=${spec#*=}
    version=${version%\*}
    if ! grep -q "^$name $version" <<< "$available"; then
      echo "MISSING $name $version for $ubuntu"
      failed=1
    fi
  done
  echo "ok $ubuntu"
done

echo "== k3s"
k3s_version=$(yq '.k3s.version' versions.yml)
sums=$(curl -fsSL "https://github.com/k3s-io/k3s/releases/download/${k3s_version/+/%2B}/sha256sum-amd64.txt")
if grep -q "^$(yq '.k3s.binary' versions.yml)  k3s$" <<< "$sums" &&
   grep -q "^$(yq '.k3s.images' versions.yml)  k3s-airgap-images-amd64.tar.zst$" <<< "$sums"; then
  echo "ok $k3s_version"
else
  echo "WRONG k3s $k3s_version sha256"
  failed=1
fi

exit $failed
