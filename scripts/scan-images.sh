#!/usr/bin/env bash
# Scan every image in versions.yml for known security problems (CVEs) with Trivy.
# Prints how many CRITICAL and HIGH problems each image has that a newer version fixes.
# It only reports: most upstream images have some, and the fix is a version bump (skill ansibro-bump).
# Needs yq and docker. CI runs it every Monday.
set -euo pipefail
cd "$(dirname "$0")/.."

trivy="aquasec/trivy:0.76.1@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c"
cache="${HOME}/.cache/trivy"  # the vulnerability list, downloaded once
mkdir -p "$cache"

report="| Image | Critical | High |\n|---|---|---|\n"
for name in $(yq '.images | keys | .[]' versions.yml); do
  image="$(yq ".images[\"$name\"].repo" versions.yml)@$(yq ".images[\"$name\"].digest" versions.yml)"
  counts=$(docker run --rm -v "$cache:/root/.cache/trivy" "$trivy" image --quiet --ignore-unfixed \
    --severity CRITICAL,HIGH --format json "$image" \
    | jq -r '[.Results[]?.Vulnerabilities[]?.Severity] | "\(map(select(. == "CRITICAL")) | length) \(map(select(. == "HIGH")) | length)"')
  read -r critical high <<< "$counts"
  echo "$name: $critical critical, $high high"
  report+="| $name | $critical | $high |\n"
done

# On GitHub, also show the table on the run's page.
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  printf "## Image scan (fixed in a newer version)\n\n%b" "$report" >> "$GITHUB_STEP_SUMMARY"
fi
