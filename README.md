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

- Ubuntu 24.04 or newer on every server
- SSH key login with passwordless sudo
- Python 3 on the machine that runs the installer (a server or your laptop)
- Internet on the servers, or an offline bundle (see [Offline install](#offline-install))

## Quick start

```bash
git clone https://github.com/sgnd/annible.git
cd annible
cp config.example.yml config.yml   # edit: servers, ssh key, domain, apps
./install.sh
```

At the end it prints how to reach each app. Then point DNS for `*.<domain>` to the
public IP of the first manager.

Run `./install.sh` again any time. It only changes what is different in `config.yml`.

> **Back up the `state/` folder.** It holds all generated passwords. If you lose it,
> the next run makes new passwords that do not match your running databases.
> Always run the installer from the same machine, or copy `state/` with it.

## Offline install

For servers with no internet (for example only VPN access).

**1. On any machine with internet and Docker** (a Mac works too), build a bundle for the
CPU and Ubuntu version of your servers:

```bash
./build-bundle.sh amd64          # Intel/AMD servers, Ubuntu 24.04
./build-bundle.sh arm64 24.04    # ARM servers
```

This makes `dist/annible-<ubuntu>-<arch>.tar.gz` (about 1 GB). It holds this project, apt packages,
Ansible and all Docker images from `versions.yml`.

**2. Copy it to the first manager** and run the installer there:

```bash
tar -xzf annible-24.04-amd64.tar.gz
cd annible
cp config.example.yml config.yml   # set tls: selfsigned (or custom)
./install.sh
```

The installer sees the `bundle/` folder and uses it instead of the internet.
The servers' own apt settings are not changed.

Notes:
- Let's Encrypt needs internet, so use `tls: selfsigned` or `tls: custom`.
- Run the installer on the first manager. It must be the same Ubuntu version and CPU as the bundle.
- Time sync (chrony) needs a time server. Without internet, point chrony at one in your network.

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
| management | [portainer](https://www.portainer.io) | swarm | | `portainer.<domain>` |
| database | [postgres](https://www.postgresql.org) / [mariadb](https://mariadb.org) | server | 5432 / 3306 | |
| cache | [redis](https://redis.io) / [valkey](https://valkey.io) | server | 6379 | |
| storage (S3) | [rustfs](https://rustfs.com) / [garage](https://garagehq.deuxfleurs.fr) | server | 9000 / 3900 | `rustfs.<domain>/rustfs/console/` |
| queue | [rabbitmq](https://www.rabbitmq.com) / [nats](https://nats.io) | server | 5672 / 4222 | `rabbitmq.<domain>` / `nats.<domain>` |

Users and password files are listed in [`catalog.yml`](catalog.yml) and printed at the end of the install.
Passwords are in `state/secrets/<app>`.

Coming next: kong, swarmpit, keycloak, authelia, uptimekuma, beszel.

## How it works

`install.sh` installs Ansible into `.venv/`, reads `config.yml` through
[`inventory.py`](inventory.py) (which also checks it), and runs [`site.yml`](site.yml):

1. **common**: hostname, packages, time sync, firewall
2. **docker**: installs Docker
3. **registry**: a private image registry on the first manager. All servers pull from it.
4. **swarm**: creates the swarm and joins the servers
5. **server apps**: `roles/<app>/`, Docker Compose in `/opt/annible/<app>/`
6. **swarm apps**: `roles/<app>/`, swarm stacks in `/opt/annible/<app>/`

### Firewall

| Open | To |
|------|----|
| SSH | `ssh.allow_from`, or anyone |
| 80, 443 | anyone, on swarm servers |
| everything | other servers in `config.yml` |

Everything else is blocked. Server apps use the host network, so the firewall controls them.

### Good to know

- **The first manager is special.** The registry, Traefik and Portainer run there.
  3 managers keep the swarm itself alive, but not those apps.
- **Use a private network between servers.** Traffic between servers is not encrypted.
- **The `ip` of a node is its private IP.** DNS must point to the public IP of the first manager.
- **Let's Encrypt** needs ports 80 and 443 reachable from the internet. Without internet use `tls: selfsigned`.

## How to

**Upgrade an app.** Change its tag and digest in `versions.yml`, then run `./install.sh`.
Major database upgrades (for example Postgres 18 to 19) need a manual dump and restore.

**Back up.** Copy `state/` (passwords) and `/opt/annible/<app>/data` on each server.
For databases, use `pg_dump` / `mariadb-dump` while they run.

**Remove an app.** Remove it from `config.yml`, then on its server:

```bash
docker stack rm <app>                           # swarm app
cd /opt/annible/<app> && docker compose down      # server app
```

Delete `/opt/annible/<app>` too if you do not need the data.
Also delete `/opt/annible/traefik/dynamic/<app>.yml` on the first manager if it exists.

**Remove a server.** Move its apps first. Then run `docker swarm leave` on it,
`docker node rm <name>` on a manager, remove it from `config.yml`, and run `./install.sh`.

**Add an app to the catalog.** See [Contributing](#contributing).

## Troubleshooting

| Problem | Try |
|---------|-----|
| `config error: ...` | The message says what to fix in `config.yml`. |
| Locked out of SSH | Check `ssh.allow_from`. Use your provider's console to run `ufw disable`. |
| No HTTPS certificate | DNS must point to the first manager, and 80/443 must be open. Let's Encrypt has rate limits. |
| App not starting | Swarm apps: `docker service ls`, `docker service logs <stack>_<service>`. Server apps: `docker ps`, `docker logs <app>`. |
| `toomanyrequests` from Docker Hub | Docker Hub limits pulls. Wait, or run `docker login` on the first manager. |

## Contributing

Rules: keep it simple, a beginner must be able to read every file. Use simple English.
Only open-source apps, every version pinned.

**Add an app:**

1. Add it to [`catalog.yml`](catalog.yml) with its license and how to reach it.
2. Add its image to [`versions.yml`](versions.yml): tag and multi-arch digest
   (`docker buildx imagetools inspect <image>:<tag>`).
3. Copy a similar role: `roles/postgres/` for a server app, `roles/portainer/` for a swarm app.
   Do not use `ports:` in server apps. Published ports skip the firewall. Use `network_mode: host`.
4. Test on a fresh VM, then run `./install.sh` a second time: it must report `changed=0`.

**Checks** (also run in CI):

```bash
ansible-lint --profile production
shellcheck install.sh
```

## License

[MIT](LICENSE). The apps it installs have their own licenses, see [THIRD_PARTY.md](THIRD_PARTY.md).
Security issues: see [SECURITY.md](SECURITY.md).
