# Annible

[![Validate](https://github.com/sgnd/annible/actions/workflows/validate.yml/badge.svg)](https://github.com/sgnd/annible/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Set up a production-ready Docker Swarm with one command.

- Works on 1 server or many.
- You pick the apps and the server each app runs on.
- Every version is pinned in [`versions.yml`](versions.yml). Nothing uses `latest`.
- Only open-source apps.
- amd64 (Intel/AMD) and arm64.
- Works without internet, with an offline bundle.

## Requirements

- Ubuntu 24.04 or 26.04 on every server. All servers use the same CPU type (all amd64 or all arm64).
- SSH key login with passwordless sudo.
- Python 3.12 or newer on the machine that runs the installer: the first manager, or your laptop.
  It must reach every server's `ip` over SSH (for example over a VPN).
- Internet on the servers and on the machine that runs the installer, or an offline bundle
  (see [Offline install](#offline-install)).
- With `tls: letsencrypt`: DNS for `*.<domain>` already points to the public IP of the first manager.

## Quick start

```bash
git clone https://github.com/sgnd/annible.git
cd annible
cp config.example.yml config.yml   # edit: servers, ssh key, domain, apps
./install.sh
```

Point DNS for `*.<domain>` to the public IP of the first manager **before** you run it, so
Let's Encrypt can check the domain. (If DNS came later: `sudo docker service update --force traefik_traefik`
on the first manager asks for the certificates again.)

At the end it prints how to reach each app, and saves it with all passwords in `state/summary.md`.

Run `./install.sh` again any time. It changes what is different in `config.yml`
(removing apps or servers is done by hand, see [How to](#how-to)).
Extra `ansible-playbook` options go after the config file, for example `./install.sh config.yml -v`.
Check mode (`--check`) is not supported.

> **Back up the `state/` folder.** It holds all generated passwords. If you lose it,
> the next run makes new passwords that do not match your running databases.
> Always run the installer from the same machine, or copy `state/` with it.

## Offline install

For servers with no internet (for example only VPN access).

**1. On a machine with internet and Docker**, build a bundle for the CPU and Ubuntu version
of your servers. A Mac (Docker Desktop or OrbStack) can build both CPU types. On Linux,
building for the other CPU type needs QEMU (`docker run --privileged --rm tonistiigi/binfmt --install all`).

```bash
./build-bundle.sh amd64          # Intel/AMD servers, Ubuntu 24.04
./build-bundle.sh arm64 26.04    # ARM servers, Ubuntu 26.04
```

This makes `dist/annible-<ubuntu>-<arch>.tar.gz` (about 2.5 GB). It holds this project, apt packages,
Ansible and all Docker images from `versions.yml`. Your project folder is not changed.

**2. Copy it to the first manager**, together with your SSH private key and, if you use them,
your `tls_cert`/`tls_key`/`acme_ca_cert` files (the bundle leaves out keys and certificates).
The installer connects over SSH to every server, the first manager itself too, so that key must
be allowed on all servers. Then run the installer there:

```bash
tar -xzf annible-24.04-amd64.tar.gz
cd annible
cp config.example.yml config.yml   # set tls: selfsigned (or custom), and ssh.key
./install.sh
```

The installer sees the `bundle/` folder and uses it instead of the internet.
The servers' own apt settings are not changed.

Notes:
- Every server must run the bundle's Ubuntu version and CPU type.
- Let's Encrypt needs internet. Use `tls: selfsigned`, `tls: custom`, or an ACME server
  in your network (`acme_server`, see `config.example.yml`).
- Time sync (chrony) needs a time server. Without internet, use one in your network: on each server
  put `server <time server ip> iburst` in `/etc/chrony/sources.d/local.sources`, then run
  `sudo chronyc reload sources`.

## Examples

**One server.** Everything on one machine:

```yaml
nodes:
  - { name: server1, ip: 10.0.0.10, role: manager }
apps:
  traefik: swarm
  portainer: swarm
  postgres: server1
  redis: server1
```

**Swarm plus a data server:**

```yaml
nodes:
  - { name: app1,  ip: 10.0.0.11, role: manager }
  - { name: app2,  ip: 10.0.0.12, role: worker }
  - { name: data1, ip: 10.0.0.21, role: standalone }
apps:
  traefik: swarm
  portainer: swarm
  postgres: data1
  rustfs: data1
```

See [`config.example.yml`](config.example.yml) for every setting.

## Apps

Pick one per category. Server apps run with Docker Compose on the server you name.
Click a name to open its official website.

| Category | App | Runs on | Port | Web page |
|----------|-----|---------|------|----------|
| gateway | [traefik](https://traefik.io/traefik/) | swarm | 80, 443 | `traefik.<domain>` |
| api-gateway | [kong](https://konghq.com/products/kong-gateway) | swarm | | `kong.<domain>`, `kong-manager.<domain>` |
| management | [portainer](https://www.portainer.io) / [swarmpit](https://swarmpit.io) | swarm | | `portainer.<domain>` / `swarmpit.<domain>` |
| auth (login) | [keycloak](https://www.keycloak.org) / [authelia](https://www.authelia.com) | swarm | | `keycloak.<domain>` / `authelia.<domain>` |
| database | [postgres](https://www.postgresql.org) / [mariadb](https://mariadb.org) | server | 5432 / 3306 | |
| cache | [redis](https://redis.io) / [valkey](https://valkey.io) | server | 6379 | |
| storage (S3) | [rustfs](https://rustfs.com) / [garage](https://garagehq.deuxfleurs.fr) | server | 9000 / 3900 | `rustfs.<domain>/rustfs/console/` |
| queue | [rabbitmq](https://www.rabbitmq.com) / [nats](https://nats.io) | server | 5672 / 4222 | `rabbitmq.<domain>` / `nats.<domain>` |
| monitoring | [uptimekuma](https://uptime.kuma.pet) / [beszel](https://beszel.dev) | server | | `uptimekuma.<domain>` / `beszel.<domain>` |

Users and password files are listed in [`catalog.yml`](catalog.yml), and printed at the end of
the install. Passwords are in `state/secrets/`, and all together in `state/summary.md`.

Some apps need others:
- Every app with a web page needs traefik (for rabbitmq, nats and rustfs only the web page does).
- kong needs postgres. keycloak needs a database. authelia needs a database and a cache.
  The installer creates their databases for them.

Swarmpit and Uptime Kuma ask you to create the admin user on your first visit, so open them
right after the install (or set `admin_allow_from` first).

**Authelia login in front of an app.** Add `authelia@file` to the app's Traefik middlewares:
for a swarm app in `roles/<app>/templates/stack.yml.j2` (the `...middlewares` label, comma-separated),
for a server app with a web page set `traefik_route_middleware: authelia@file` in `roles/<app>/tasks/main.yml`.
A server app has one middleware, so this replaces its `admin_allow_from` limit.

## How it works

`install.sh` installs Ansible into `.venv/`, reads `config.yml` through
[`inventory.py`](inventory.py) (which also checks it), and runs [`site.yml`](site.yml):

1. **bundle** (offline only): copies the bundle to the servers
2. **common**: hostname, packages, time sync, firewall
3. **docker**: installs Docker
4. **registry**: a private image registry on the first manager. All servers pull from it.
5. **swarm**: creates the swarm and joins the servers
6. **server apps**: `roles/<app>/`, Docker Compose in `/opt/annible/<app>/`
7. **beszel agents** (if beszel is picked): on every server
8. **swarm apps**: `roles/<app>/`, swarm stacks in `/opt/annible/<app>/`

### Firewall

| Open | To |
|------|----|
| SSH | `ssh.allow_from`, or anyone |
| 80, 443 | anyone, on swarm servers |
| everything | other servers in `config.yml` |
| everything | containers on the same server (`docker0`, `docker_gwbridge`) |

Everything else is blocked. Server apps use the host network, so the firewall controls them.
Admin web pages can be limited to some IPs with `admin_allow_from`.

### Good to know

- **The first manager is special.** The registry, Traefik, Portainer, Authelia and Swarmpit's
  databases run there and keep their data there. 3 managers keep the swarm itself alive, but not those apps.
- **Use a private network between servers.** Traffic between servers is not encrypted.
- **The `ip` of a node is its private IP.** DNS must point to the public IP of the first manager.
- **Let's Encrypt** needs port 80 reachable from the internet. Without internet use `tls: selfsigned`.

## How to

**Upgrade an app.** Change its tag and digest in `versions.yml`, then run `./install.sh`.
Major Postgres upgrades (for example 18 to 19) need a manual dump and restore.

Commands on the servers need `sudo`: the installer does not add users to the `docker` group,
and `/opt/annible/<app>/` is readable by root only.

**Back up.** Copy `state/` (passwords) from the installer machine, and on each server
`sudo tar -czf <app>.tgz -C /opt/annible <app>`.
For databases, use `pg_dump` / `mariadb-dump` while they run.

**Remove an app.** Remove it from `config.yml`, then:

```bash
sudo docker stack rm <app>                                      # swarm app, on the first manager
sudo docker compose -f /opt/annible/<app>/compose.yml down      # server app, on its server
```

If you do not need the data: `sudo rm -rf /opt/annible/<app>` on its server, and
`sudo rm -f /opt/annible/traefik/dynamic/<app>.yml` on the first manager.
For beszel, also run `sudo docker compose -f /opt/annible/beszel-agent/compose.yml down` on every server.

**Remove a server.** Move its apps to other servers first, then remove it from `config.yml`.
- Worker: run `sudo docker swarm leave` on it, then `sudo docker node rm <name>` on a manager.
- Manager: first `sudo docker node demote <name>` on another manager, then the same as a worker.
- Standalone: nothing else to do.

Run `./install.sh` again, so the firewall forgets the removed server.

**Add a server.** Add it to `config.yml` and run `./install.sh`.

## Troubleshooting

| Problem | Try |
|---------|-----|
| `config error: ...` | The message says what to fix in `config.yml`. |
| Locked out of SSH | Check `ssh.allow_from`. Use your provider's console to run `sudo ufw disable`. |
| No HTTPS certificate | DNS must point to the first manager, and port 80 must be open. Then run `sudo docker service update --force traefik_traefik` on the first manager. Let's Encrypt has rate limits. |
| App not starting | Swarm apps: `sudo docker service ls`, `sudo docker service logs <stack>_<service>`. Server apps: `sudo docker ps`, `sudo docker logs <app>`. |
| `toomanyrequests` from Docker Hub | Docker Hub limits pulls. Wait, or run `sudo docker login` on the first manager. |

## Testing

After an install, check every app for real (logins, databases, S3 keys, web pages).
Run it where you ran `./install.sh`, in the same folder:

```bash
.venv/bin/python tests/check.py          # or: .venv/bin/python tests/check.py other.yml
```

It prints PASS or FAIL for each check. The checks run on the first manager
(over SSH if you are on another machine), because the firewall only lets cluster servers reach the apps.

## Contributing

Rules: keep it simple, a beginner must be able to read every file. Use simple English.
Only open-source apps, every version pinned.

**Add an app:**

1. Add it to [`catalog.yml`](catalog.yml) with its license and how to reach it.
2. Add its image to [`versions.yml`](versions.yml): tag and multi-arch digest
   (`docker buildx imagetools inspect <image>:<tag>`).
3. Copy a similar role: `roles/postgres/` for a server app, `roles/portainer/` for a swarm app.
   Do not use `ports:` in server apps. Published ports skip the firewall. Use `network_mode: host`.
4. Add it to the Apps table above, to [`THIRD_PARTY.md`](THIRD_PARTY.md), to
   [`config.example.yml`](config.example.yml), and a check to [`tests/check.py`](tests/check.py).
5. Test on a fresh VM: run `./install.sh` two times (the second run must report `changed=0`),
   then `.venv/bin/python tests/check.py`.

**AI agents.** [`.claude/skills/`](.claude/skills) has skills for Claude Code and other agents
that read `SKILL.md`: set up `config.yml`, install, add an app, and update versions.

**Checks** (also run in CI, see [`validate.yml`](.github/workflows/validate.yml)).
No servers needed. The first line makes `.venv/` with Ansible:

```bash
./install.sh config.example.yml --syntax-check
.venv/bin/pip install ansible-lint
.venv/bin/python tests/test_config.py      # config.example.yml works, mistakes are refused
ANNIBLE_CONFIG=config.example.yml PATH="$PWD/.venv/bin:$PATH" ansible-lint --profile production
shellcheck install.sh build-bundle.sh scripts/*.sh
scripts/validate-versions.sh               # needs yq, docker and curl
```

## License

[MIT](LICENSE). The apps it installs have their own licenses, see [THIRD_PARTY.md](THIRD_PARTY.md).
Security issues: see [SECURITY.md](SECURITY.md).
