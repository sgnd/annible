---
name: annible-install
description: Run the Annible installer, online or offline (bundle), and fix common problems. Use when someone wants to install, re-run, build an offline bundle, or debug a failed install.
---

# Install Annible

The installer changes real servers. **Ask the user before you run `./install.sh`.**

## Before you start

- `config.yml` exists and is valid. If not, use the `annible-setup` skill first.
- Servers run Ubuntu 24.04 or newer, with SSH key login and passwordless sudo.
- Always run it from the same machine, because the `state/` folder holds all passwords.

## Online (servers have internet)

```bash
./install.sh                 # uses config.yml
./install.sh other.yml       # another config file
```

You can run it again any time. It only changes what is different in `config.yml`.

## Offline (no internet on the servers)

1. On a machine with internet and Docker (a Mac works too), build the bundle for the **servers'** CPU and Ubuntu version:

   ```bash
   ./build-bundle.sh amd64          # Intel/AMD, Ubuntu 24.04
   ./build-bundle.sh arm64 24.04    # ARM
   ```

   This makes `dist/annible-<ubuntu>-<arch>.tar.gz` (about 1 GB).
2. Copy it to the **first manager**, unpack it, add `config.yml` with `tls: selfsigned` (or `custom`), then run `./install.sh` there.

The installer sees the `bundle/` folder and uses it instead of the internet.

## After the install

- Read `state/summary.md`. It lists every app's address and passwords. Don't paste the passwords into chat.
- Tell the user to **back up `state/`**. If it is lost, the next run makes new passwords that don't match the running databases.
- DNS for `*.<domain>` must point to the public IP of the first manager.
- Swarmpit and Uptime Kuma ask for an admin user on the first visit. Open them right away.

## When it fails

| Problem | Try |
|---------|-----|
| `config error: ...` | Fix `config.yml` as the message says. |
| Wrong CPU or Ubuntu version | `arch` in config.yml must match the servers. Offline: rebuild the bundle for that version. |
| Locked out of SSH | Check `ssh.allow_from`. Use the provider's console to run `ufw disable`. |
| No HTTPS certificate | DNS must point to the first manager, and 80/443 must be open. Let's Encrypt has rate limits. |
| Swarm app not starting | `docker service ls`, `docker service logs <stack>_<service>` on a manager. |
| Server app not starting | `docker ps`, `docker logs <app>` on that server. |
| `toomanyrequests` | Docker Hub limit. Wait, or run `docker login` on the first manager. |

Read the failed Ansible task name first. It usually says what went wrong.
