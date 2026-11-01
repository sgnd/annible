# How it works

What the installer does, step by step, and things good to know.

`install.sh` installs Ansible into `.venv/`, reads `config.yml` through
[`inventory.py`](../inventory.py) (which also checks it), and runs [`site.yml`](../site.yml):

1. **removed servers** leave the cluster (only with `-e remove_nodes=true`)
2. **bundle** (offline only): copies the bundle to the servers
3. **common**: hostname, packages, time sync, firewall
4. **wireguard** (if `wireguard: true`): the encrypted network between the servers
5. **gpu** (servers with `gpu: true`): NVIDIA driver and container toolkit
6. **docker**: installs Docker
7. **registry**: a private image registry on every manager, with the same images. All servers pull from it.
8. **swarm** or **k3s**: creates the cluster and joins the servers
9. **server apps**: `roles/<app>/`, Docker Compose in `/opt/ansibro/<app>/`
10. **agents** on every server: beszel (if picked), monitoring (with prometheus or victoria)
11. **swarm apps**: `roles/<app>/`, swarm stacks in `/opt/ansibro/<app>/` (k3s: its built-in Traefik)
12. **removed apps** stop, then **backup** (if `backup:` is set)

## Firewall

| Open | To |
|------|----|
| SSH | `ssh.allow_from`, or anyone |
| 80, 443 | anyone, on swarm servers |
| the ports a server needs: swarm, registry, its apps, monitoring agents | other servers in `config.yml` (from their `ip`) |
| UDP 51820 | other servers' `host`, with `wireguard: true` |
| everything | containers on the same server (Docker's own internal networks) |
| your own ports | `firewall_allow` in `config.yml` (for example a VPN) |

Everything else is blocked. Server apps use the host network, so the firewall controls them.
Even between your servers only those ports are open (the list is `common_app_ports` in
`roles/common/defaults/main.yml`). An app of your own on a server's host network needs a `firewall_allow` rule.
Admin web pages can be limited to some IPs with `admin_allow_from`.

The installer owns the firewall. The first run, and every run where the rules change, resets it:
rules you added by hand are removed (put them in `firewall_allow`). During that reset the firewall
is off for a few seconds.

**Warning:** a port you open yourself with `docker run -p`, or with `ports:` in your own swarm stack,
is open to everyone: the firewall cannot block it (that is how Docker works). Use Traefik for web apps.

## Good to know

- **The first manager is special.** Portainer, Authelia and Swarmpit's databases run there and
  keep their data there. Keep it first in the `nodes` list: the installer stops if the first manager
  is not the one that made the swarm.
- **With 3 managers, one can go down.** The swarm keeps working, and every manager has the registry
  with all images.
- **Where Traefik runs.** With `tls: letsencrypt`, Traefik runs only on the first manager: point DNS there.
  (Let's Encrypt checks a domain by calling it, and the call could reach another manager.)
  With `tls: selfsigned` or `tls: custom` (for example a wildcard certificate), Traefik runs on every
  manager: point DNS to all of them.
- **Tiers.** Swarm servers that run server apps get the label `tier=data`, the others `tier=app`.
  Kong and Keycloak run on `tier=app` servers when there are any. Use `node.labels.tier == app`
  in your own stacks too. Set `labels: { tier: ... }` on a node to choose yourself.
- **The registry needs a login.** Every server logs in (password in `state/secrets/registry`),
  so a container cannot push a fake image into it.
- **Swarm networks use `10.200.0.0/16`, k3s uses `10.42.0.0/16` and `10.43.0.0/16`.** Your servers' IPs must be outside them.
- **Use a private network between servers, or `wireguard: true`.** Without WireGuard, traffic between servers is not encrypted.
- **The `ip` of a node is its private IP** (or its WireGuard address). DNS must point to the public IP of the servers Traefik runs on.
- **A swarm server cannot change its `ip`.** The installer stops if a server's swarm address differs from `ip`
  (for example after a snapshot restore on a new IP). With `wireguard: true` you only change `host`.
- **Network size (MTU, the biggest network packet) is set for you.** Swarm networks use the smallest MTU of the servers minus 50
  (1370 with WireGuard), so big requests do not hang. This applies to networks the installer creates.
  For your own overlay networks, add `driver_opts: { com.docker.network.driver.mtu: "1370" }` with WireGuard.
- **On cloud servers** the installer tells cloud-init to keep the hostname after a reboot, because
  swarm apps are placed by hostname.
- **Let's Encrypt** needs port 80 reachable from the internet. Without internet use `tls: selfsigned`.

## Files in this repo

| File or folder | What it is |
|----------------|------------|
| `install.sh` | The installer you run. It installs Ansible in `.venv/` and runs `site.yml`. |
| `config.example.yml` | The example config. Copy it to `config.yml`. |
| `inventory.py` | Reads and checks `config.yml`, and tells Ansible about your servers. |
| `site.yml` | The list of steps (the Ansible playbook). |
| `roles/` | One folder per step or app, with its tasks and files. |
| `catalog.yml` | All apps: category, where they run, license, how to reach them. |
| `versions.yml` | Every pinned version: images, packages, k3s. |
| `group_vars/`, `templates/`, `ansible.cfg` | Settings shared by all steps, the summary template, Ansible's settings. |
| `requirements.txt`, `requirements.yml` | The Python packages (Ansible) and Ansible add-ons the installer downloads. |
| `build-bundle.sh` | Builds an offline bundle. |
| `scripts/` | Small helpers: open and close `state/`, check versions, scan images. |
| `tests/` | `check.py` checks a real install; `test_config.py` checks `config.yml` mistakes. |
| `.claude/skills/` | Help for AI agents (set up, install, add an app, update versions). |
