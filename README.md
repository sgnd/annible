# Annible

[![Validate](https://github.com/sgnd/annible/actions/workflows/validate.yml/badge.svg)](https://github.com/sgnd/annible/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Set up a production-ready Docker Swarm with one command.

- Works on 1 server or many.
- You pick the apps and the server each app runs on.
- Every version is pinned in [`versions.yml`](versions.yml). Nothing uses `latest`.
- Only open-source apps.
- amd64 (Intel/AMD) and arm64, also mixed in one cluster.
- Works without internet, with an offline bundle.

## Requirements

- Ubuntu 24.04 or 26.04 on every server. Servers can be amd64 or arm64; the installer finds out
  which. With internet they can mix. The offline bundle needs one CPU type for all servers.
- SSH key login with passwordless sudo.
- Python 3.12 or newer on the machine that runs the installer: the first manager, or your laptop.
  It must reach every server over SSH: its `host`, or its `ip` if it has no `host` (for example over a VPN).
- Internet on the servers and on the machine that runs the installer (it uses PyPI and Ansible Galaxy), or an offline bundle
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

**Servers with more than one IP** (for example AWS: a public IP for SSH, a private IP inside the VPC).
`ip` is what the swarm uses, `host` is where the installer connects:

```yaml
nodes:
  - { name: app1, ip: 10.0.0.11, host: 203.0.113.11, role: manager }
  - { name: app2, ip: 10.0.0.12, host: 203.0.113.12, role: worker }
```

**Encrypted network between servers** (WireGuard). For servers that talk over the internet,
in different clouds, or that may move. `host` is the server's real address, `ip` is a new
address on the WireGuard network that you pick, and it never has to change:

```yaml
wireguard: true
nodes:
  - { name: app1,  ip: 10.99.0.11, host: 203.0.113.11, role: manager }
  - { name: app2,  ip: 10.99.0.12, host: 198.51.100.7, role: worker }
  - { name: data1, ip: 10.99.0.21, host: 192.0.2.30,   role: standalone }
```

Each `host` must be reachable from the other servers (WireGuard) and from the installer (SSH).
Open UDP port 51820 between the servers' `host` addresses in your cloud firewall (security group).
Turn it on for a new cluster: an existing swarm cannot change its servers' addresses.

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
| observability (metrics, logs, alerts) | [prometheus](https://prometheus.io) (+ Loki) / [victoria](https://victoriametrics.com) (VictoriaMetrics + VictoriaLogs), both with Alertmanager and Grafana | server | | `grafana.<domain>`, `alertmanager.<domain>`, `metrics.<domain>` (+ `logs.<domain>` for victoria) |

Users and password files are listed in [`catalog.yml`](catalog.yml), and printed at the end of
the install. Passwords are in `state/secrets/`, and all together in `state/summary.md`.

Some apps need others:
- Every app with a web page needs traefik (for rabbitmq, nats and rustfs only the web page does).
- kong needs postgres. keycloak needs a database. authelia needs a database and a cache.
  The installer creates their databases for them.

Swarmpit and Uptime Kuma create their admin user on the first visit. So their pages first ask for
the Traefik dashboard login (user `admin`, password in `state/secrets/traefik_admin`); after that you
create the app's own admin user.

**Kong** runs on its own network, `kong`, shared only with Traefik. Put your API services on that
network too (`networks: [kong]`, external) so Kong can reach them. Other apps cannot reach Kong's admin API.

**Swarmpit** needs CouchDB 2.3 and InfluxDB 1.8, which are old. They are only on Swarmpit's own
network, but if you want only up-to-date software, choose Portainer.

**Authelia login in front of an app.** Add `authelia@file` to the app's Traefik middlewares:
for a swarm app in `roles/<app>/templates/stack.yml.j2` (the `...middlewares` label, comma-separated),
for a server app with a web page set `traefik_route_middleware: authelia@file` in `roles/<app>/tasks/main.yml`.
A server app has one middleware, so this replaces its `admin_allow_from` limit.

## How it works

`install.sh` installs Ansible into `.venv/`, reads `config.yml` through
[`inventory.py`](inventory.py) (which also checks it), and runs [`site.yml`](site.yml):

1. **bundle** (offline only): copies the bundle to the servers
2. **common**: hostname, packages, time sync, firewall
3. **wireguard** (if `wireguard: true`): the encrypted network between the servers
4. **docker**: installs Docker
5. **registry**: a private image registry on the first manager. All servers pull from it.
6. **swarm**: creates the swarm and joins the servers
7. **server apps**: `roles/<app>/`, Docker Compose in `/opt/annible/<app>/`
8. **beszel agents** (if beszel is picked): on every server
9. **swarm apps**: `roles/<app>/`, swarm stacks in `/opt/annible/<app>/`

### Firewall

| Open | To |
|------|----|
| SSH | `ssh.allow_from`, or anyone |
| 80, 443 | anyone, on swarm servers |
| everything | other servers in `config.yml` (from their `ip`) |
| UDP 51820 | other servers' `host`, with `wireguard: true` |
| everything | containers on the same server (`docker0`, `docker_gwbridge`) |
| your own ports | `firewall_allow` in `config.yml` (for example a VPN) |

Everything else is blocked. Server apps use the host network, so the firewall controls them.
Admin web pages can be limited to some IPs with `admin_allow_from`.

The installer owns the firewall. The first run, and every run where the rules change, resets it:
rules you added by hand are removed (put them in `firewall_allow`). During that reset the firewall
is off for a few seconds. Ports you publish yourself with `docker run -p` or in your own swarm
stacks skip the firewall (that is how Docker works), so prefer Traefik for web apps.

### Good to know

- **The first manager is special.** The registry, Traefik, Portainer, Authelia and Swarmpit's
  databases run there and keep their data there. 3 managers keep the swarm itself alive, but not those apps.
  Keep it first in the `nodes` list: the installer stops if the first manager is not the one that made the swarm.
- **The registry needs a login.** Every server logs in (password in `state/secrets/registry`),
  so a container cannot push a fake image into it.
- **Swarm networks use `10.200.0.0/16`.** Your servers' IPs must be outside that range.
- **Use a private network between servers, or `wireguard: true`.** Without WireGuard, traffic between servers is not encrypted.
- **The `ip` of a node is its private IP** (or its WireGuard address). DNS must point to the public IP of the first manager.
- **A swarm server cannot change its `ip`.** The installer stops if a server's swarm address differs from `ip`
  (for example after a snapshot restore on a new IP). With `wireguard: true` you only change `host`.
- **Network size (MTU) is set for you.** Swarm networks use the smallest MTU of the servers minus 50
  (1370 with WireGuard), so big requests do not hang. This applies to networks the installer creates.
  For your own overlay networks, add `driver_opts: { com.docker.network.driver.mtu: "1370" }` with WireGuard.
- **On cloud servers** the installer tells cloud-init to keep the hostname after a reboot, because
  swarm apps are placed by hostname.
- **Let's Encrypt** needs port 80 reachable from the internet. Without internet use `tls: selfsigned`.

## How to

**Upgrade an app.** Change its tag and digest in `versions.yml`, then run `./install.sh`.
Major Postgres upgrades (for example 18 to 19) need a manual dump and restore.
A new Docker version is installed one server at a time, so the swarm keeps running.

Commands on the servers need `sudo`: the installer does not add users to the `docker` group,
and the passwords and data in `/opt/annible/` are readable by root only.

**Back up and restore.** Add `backup:` to `config.yml` (see [`config.example.yml`](config.example.yml))
and run `./install.sh`. Every server then backs up each night with [restic](https://restic.net)
(encrypted), and the install runs the first backup right away. What is saved:

- databases (PostgreSQL, MariaDB) as a dump, while they run
- every other folder in `/opt/annible/`: the app is paused for a moment while its files are copied
- RustFS and Garage data as it is, while it runs
- on the first manager: the swarm (your stacks, secrets, configs, networks), `config.yml` and `state/`

Not saved: the image registry (the installer fills it again; push your own images again from CI)
and Docker volumes. Keep your own stacks' files in `/opt/annible/<stack name>/` so they are saved too:
their containers are paused while copied, like the apps above.

```bash
sudo annible-backup              # back up now
sudo annible-backup snapshots    # list the backups
```

To move the cluster to new servers, or after you lost it: make new servers, keep the same node names
and `ip` values (with `wireguard: true` only `host` changes), keep `state/`, and run:

```bash
./install.sh -e restore=true
```

Each server gets its newest backup back, the swarm comes back with your stacks, and the databases are
loaded from their dumps. Old servers are removed from the swarm. A restore only runs on new servers.
If you lost `state/` too, get it from the backup with the restic password (`state/secrets/restic`):
`restic -r <repository> restore latest --host <first manager> --include /opt/annible/backup/stage/installer --target .`

**Monitoring and alerts.** Add `prometheus` or `victoria` to `apps` (on a server with at least 2 GB
of free memory), and `monitoring:` with where alerts go: Telegram, email or a webhook (Slack and Discord
URLs are found by themselves). See [`config.example.yml`](config.example.yml). Both choices do the same;
victoria uses less memory and disk.

On every server, agents collect the server (CPU, memory, disk, clock), its containers, the logs of
every container and of the system, and the stats of PostgreSQL, MariaDB, Redis and Valkey. Each minute,
every server also checks that its apps answer on their port, and writes the state of the swarm, the
last backup and WireGuard. Alerts are sent for:

- a server, an app, a container or a swarm service that is down, or restarts again and again
- a disk that is almost full (or fills up within a day), memory or CPU that stays high, a wrong clock
- a backup older than 26 hours, a WireGuard link that is down, a certificate that ends within 14 days
- a database or cache that is down or out of connections, web apps that answer with errors
- the monitoring itself: an agent or exporter that does not answer, alerts that cannot be sent

The rules are in [`roles/observability/files/alerts.yml`](roles/observability/files/alerts.yml).
Grafana has an "Annible overview" dashboard. Logs: Grafana > Explore (prometheus), or
`https://logs.<domain>/select/vmui` (victoria).

**Who watches the monitoring?** If the monitoring server stops, it cannot send an alert. So the
`Watchdog` alert is always firing, and something on another server checks that it still is:

- Uptime Kuma (put `uptimekuma` on another server): add a monitor of type "HTTP(s) - Keyword",
  URL `http://<monitoring server ip>:9093/api/v2/alerts?filter=alertname=Watchdog`, keyword `Watchdog`.
  The install prints this URL. When the monitoring server, Alertmanager or the alert rules stop,
  the keyword is gone and Uptime Kuma tells you. The monitoring server sends an alert when Uptime Kuma's
  server is down, so the two watch each other.
- Or a heartbeat service outside the cluster, like [healthchecks.io](https://healthchecks.io): put its URL
  in `monitoring.heartbeat_url`. Alertmanager sends it a POST about every 2 minutes; set its period to 5 minutes.
  (Uptime Kuma's "Push" monitor does not work here: it takes only GET.)

**Remove an app.** Remove it from `config.yml`, then:

```bash
sudo docker stack rm <app>                                      # swarm app, on the first manager
sudo docker compose -f /opt/annible/<app>/compose.yml down      # server app, on its server
```

If you do not need the data: `sudo rm -rf /opt/annible/<app>` on its server, and
`sudo rm -f /opt/annible/traefik/dynamic/<app>.yml` on the first manager.
For beszel, also run `sudo docker compose -f /opt/annible/beszel-agent/compose.yml down` on every server.
For prometheus or victoria, also run `sudo docker compose -f /opt/annible/monitoring-agent/compose.yml down`
and `sudo systemctl disable --now annible-metrics.timer` on every server.
Not removed by itself: the app's database (drop it in Postgres or MariaDB), its old images in the
registry, a server in Beszel's list (delete it in Beszel), and ports 80/443 if you remove traefik.

**Remove a server.** Move its apps to other servers first, then remove it from `config.yml`.
- Worker: run `sudo docker swarm leave` on it, then `sudo docker node rm <name>` on a manager.
- Manager: first `sudo docker node demote <name>` on another manager, then the same as a worker.
- Standalone: nothing else to do.

Run `./install.sh` again, so the firewall forgets the removed server. Never remove the first manager.

**Add a server.** Add it to `config.yml`, after the first manager, and run `./install.sh`.

**Change a server's role** (worker to manager or back). The installer does not do this; it stops and
shows the command: `sudo docker node promote <name>` or `sudo docker node demote <name>` on a manager.

## Troubleshooting

| Problem | Try |
|---------|-----|
| `config error: ...` | The message says what to fix in `config.yml`. |
| Locked out of SSH | Check `ssh.allow_from`. Use your provider's console to run `sudo ufw disable`. |
| `cannot reach ... over WireGuard` | Open UDP 51820 between the servers' `host` addresses in your cloud firewall. `sudo wg show` shows the last handshake. |
| No HTTPS certificate | DNS must point to the first manager, and port 80 must be open. Then run `sudo docker service update --force traefik_traefik` on the first manager. Let's Encrypt has rate limits. |
| App not starting | Swarm apps: `sudo docker service ls`, `sudo docker service logs <stack>_<service>`. Server apps: `sudo docker ps`, `sudo docker logs <app>`. |
| `no such host` or a timeout while downloading | A network problem on the server. Check its internet, then run `./install.sh` again. It is safe to run again: it continues where it stopped. |
| No alerts arrive | Look at `https://alertmanager.<domain>`: if alerts are there, check `monitoring:` in `config.yml` and the `AlertsNotSent` alert. Logs: `sudo docker logs alertmanager` on the monitoring server. |
| An alert you do not want | Silence it in `https://alertmanager.<domain>` (for a time), or change the rule in `roles/observability/files/alerts.yml`. |
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
.venv/bin/pip install ansible-lint==26.10.1
.venv/bin/python tests/test_config.py      # config.example.yml works, mistakes are refused
ANNIBLE_CONFIG=config.example.yml PATH="$PWD/.venv/bin:$PATH" ansible-lint --profile production
shellcheck install.sh build-bundle.sh scripts/*.sh
scripts/validate-versions.sh               # needs yq, docker and curl
```

## License

[MIT](LICENSE). The apps it installs have their own licenses, see [THIRD_PARTY.md](THIRD_PARTY.md).
Changes: see [CHANGELOG.md](CHANGELOG.md).
Security issues: see [SECURITY.md](SECURITY.md).
