---
name: annible-install
description: Run the Annible installer, online or offline (bundle), and fix common problems. Use when someone wants to install, re-run, build an offline bundle, or debug a failed install.
---

# Install Annible

The installer changes real servers. **Ask the user before you run `./install.sh`.**

## Before you start

- `config.yml` exists and is valid. If not, use the `annible-setup` skill first.
- Servers run Ubuntu 24.04 or 26.04, all with the same CPU type, with SSH key login and passwordless sudo.
- The machine that runs the installer has Python 3.12 or newer and can reach every server's `ip` over SSH.
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
   ./build-bundle.sh arm64 26.04    # ARM, Ubuntu 26.04
   ```

   This makes `dist/annible-<ubuntu>-<arch>.tar.gz` (about 2.5 GB).
2. Copy it **and the SSH private key** to the **first manager** (plus any `tls_cert`, `tls_key` or
   `acme_ca_cert` files: the bundle leaves out keys and certificates). The key must be allowed on
   every server, the first manager itself too. Unpack, add `config.yml` with `tls: selfsigned`
   (or `custom`, or `acme_server`) and `ssh.key` pointing at the key, then run `./install.sh` there.

The installer sees the `bundle/` folder and uses it instead of the internet.

## After the install

- Run `.venv/bin/python tests/check.py` where you ran `./install.sh`. Every check must PASS.
- Read `state/summary.md`. It lists every app's address and passwords. Don't paste the passwords into chat.
- Tell the user to **back up `state/`**. If it is lost, the next run makes new passwords that don't match the running databases.
- DNS for `*.<domain>` must point to the public IP of the first manager. With Let's Encrypt it must be
  set before the install; if it came later, run `sudo docker service update --force traefik_traefik` on the first manager.
- Swarmpit and Uptime Kuma first ask for the Traefik dashboard login (user admin), then for a new admin user of their own.

## When it fails

| Problem | Try |
|---------|-----|
| `config error: ...` | Fix `config.yml` as the message says. |
| Wrong CPU or Ubuntu version | `arch` in config.yml must match the servers. Offline: rebuild the bundle for that version. |
| Locked out of SSH | Check `ssh.allow_from`. Use the provider's console to run `sudo ufw disable`. |
| No HTTPS certificate | DNS must point to the first manager, and port 80 must be open. Then `sudo docker service update --force traefik_traefik`. Let's Encrypt has rate limits. |
| Swarm app not starting | `sudo docker service ls`, `sudo docker service logs <stack>_<service>` on a manager. |
| Server app not starting | `sudo docker ps`, `sudo docker logs <app>` on that server. |
| `toomanyrequests` | Docker Hub limit. Wait, or run `sudo docker login` on the first manager. |
| `cannot reach ... over WireGuard` | Open UDP 51820 between the servers' `host` addresses in the cloud firewall (security group). Check each `host`. `sudo wg show` on a server shows the last handshake. |
| `is in the swarm with address ...` | A swarm server cannot change its address. Put the old address back as `ip`. If the server's real address changed, set it as `host`. |

Read the failed Ansible task name first. It usually says what went wrong.
