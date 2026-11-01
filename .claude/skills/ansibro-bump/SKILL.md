---
name: ansibro-bump
description: Update a pinned version in Ansibro's versions.yml (Docker image tag and digest, or Docker apt packages). Use when someone wants to upgrade an app, update images, or fix a pinned version that no longer exists.
---

# Update a pinned version

All versions are in `versions.yml`. Nothing uses `latest`.

## Docker image

1. Find the new **stable** tag on the app's releases page or Docker Hub. Skip `rc`, `beta`, `alpha`, `edge` and `latest`.
2. Get the multi-arch digest:

   ```bash
   docker buildx imagetools inspect docker.io/library/redis:8.10.4
   ```

   Use the top `Digest:` (the index). Check that `linux/amd64` and `linux/arm64` are both listed.
3. Change **both** `tag` and `digest` in `versions.yml`. The local registry is checked by tag, so a new digest with the old tag is not picked up.
4. Keep quotes on tags that look like numbers, for example `tag: "18.6"`.

Some apps have two images with the same version (for example `portainer` and `portainer-agent`). Bump them together.

## Big upgrades: warn the user

- **Major Postgres versions** (18 to 19) need a manual dump and restore. Don't bump these without asking.
  MariaDB upgrades its data files by itself (`MARIADB_AUTO_UPGRADE=1`), but still take a backup first.
- Read the release notes for breaking changes in config or data.
- Check the license did not change to a non-open-source one.

## Docker apt packages

`docker_packages` uses `name=version*`. Find versions at
`https://download.docker.com/linux/ubuntu/dists/<noble|resolute>/stable/binary-<amd64|arm64>/Packages`.
The same version must exist for Ubuntu 24.04 (noble) and 26.04 (resolute).
Keep `docker-ce` and `docker-ce-cli` on the same version.

## Check

```bash
scripts/validate-versions.sh      # needs yq, docker and curl
```

It checks every image has amd64 and arm64, and every apt package exists for both Ubuntu versions.
Then run `./install.sh` on a test VM. Offline users need a new bundle (`./build-bundle.sh <amd64|arm64> <24.04|26.04>`).
