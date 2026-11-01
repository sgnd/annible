---
name: ansibro-add-app
description: Add a new app to the Ansibro catalog (a new role, catalog entry and pinned image). Use when someone wants Ansibro to support a new tool, like a database, gateway, queue or monitoring app.
---

# Add an app to Ansibro

## Rules (check these first)

- **Open source only.** The license must be OSI-approved. If it is not (for example BSL or SSPL), stop and tell the user.
- **Pinned version.** Tag + multi-arch digest (amd64 and arm64). Never `latest`.
- **Works offline.** Images come from `versions.yml`, so the bundle and the local registry pick them up. Don't download anything else at install time.
- **Apps with data** (databases, caches, storage, queues, monitoring) use `runs_on: node` and Docker Compose.
  A swarm app that must keep data is pinned to the first manager (see `roles/portainer/`).
- **Keep it simple.** A beginner must be able to read every file. Simple English in comments.
- Each category has two choices at most. The popular one comes first.

## Steps

1. **catalog.yml**: add the app next to the other app of its category. (The installer deploys
   all server apps first, then all swarm apps, so a swarm app can use a server app's database.)

   ```yaml
   myapp:
     category: cache
     runs_on: node            # or swarm
     requires: [traefik]      # needed if it has a web page; can also name a category, e.g. database
     license: MIT
     info: "<ip>:1234 (password state/secrets/myapp)"
   ```

2. **versions.yml**: add the image under `images:`. Get the digest of the multi-arch index:

   ```bash
   docker buildx imagetools inspect docker.io/org/myapp:1.2.3
   ```

   Use the top `Digest:` (the index), not one of the per-platform digests. Check that both `linux/amd64` and `linux/arm64` are listed.

3. **roles/myapp/**: copy the closest role and rename things.
   - Server app: copy `roles/valkey/` (simple) or `roles/postgres/` (has a database).
   - Server app with a web page: copy `roles/uptimekuma/` (uses `traefik` `tasks_from: route`).
   - Swarm app: copy `roles/portainer/` (stack file + `swarm` `tasks_from: deploy`).
   - Pull the image with the `registry` role `tasks_from: mirror`. In templates use `{{ registry_addr }}/myapp:{{ images.myapp.tag }}`.
   - Passwords: `lookup('ansible.builtin.password', secrets_dir ~ '/myapp', ...)` in `defaults/main.yml`.
   - Server apps: use `network_mode: host`, **never `ports:`**. Published ports skip the firewall.
   - Add `diff: false` or `no_log: true` to tasks that write passwords.

4. **Docs**:
   - `README.md`: add a row to the Apps table.
   - `THIRD_PARTY.md`: add name, license and source link.
   - `config.example.yml`: mention it as a comment next to the other app in its category.
   - `tests/check.py`: add a check that logs in to it for real.

## Check

No servers needed. The first line makes `.venv/` with Ansible:

```bash
./install.sh config.example.yml --syntax-check
.venv/bin/pip install ansible-lint==26.10.1
.venv/bin/python tests/test_config.py
ANSIBRO_CONFIG=config.example.yml PATH="$PWD/.venv/bin:$PATH" ansible-lint --profile production
shellcheck install.sh build-bundle.sh scripts/*.sh
scripts/validate-versions.sh               # needs yq, docker and curl
```

Then test on a fresh VM: run `./install.sh` two times. The second run must show `changed=0`.
Then run `.venv/bin/python tests/check.py` where you ran `./install.sh`: every check must PASS.
