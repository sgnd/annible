# Ansibro

[![Validate](https://github.com/sgnd/ansibro/actions/workflows/validate.yml/badge.svg)](https://github.com/sgnd/ansibro/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Set up your servers to run apps, with one command.

## What is it?

You have one or more Linux servers, and you want to run apps on them: your own apps, and the
usual helpers like a web gateway, a database and monitoring. By hand that is a lot of work:
install Docker, join the servers into a cluster, set up a firewall, HTTPS, passwords, backups and alerts.

Ansibro does all of that for you. You write what you want in one file, `config.yml`, and run
`./install.sh`. At the end you get the web address and password of every app.

**Who is it for?** Anyone who can use a terminal and log in to a server with SSH.
You do not need to know Ansible, Docker Swarm or Kubernetes.

**New to this?** Start with [Getting started](docs/getting-started.md): a step-by-step first install,
from renting a server to opening your first app. Words you do not know are explained in
[Words](docs/getting-started.md#words).

**What you get:**

- A Docker Swarm cluster (the default), or k3s (a small Kubernetes).
- 1 server or many. You pick the apps and the server each app runs on.
- A firewall, HTTPS, and a password for every app, made for you.
- Optional: backups each night, monitoring with alerts, an encrypted network between servers.
- Only open-source apps. Every version is pinned in [`versions.yml`](versions.yml), nothing uses `latest`.
- Intel/AMD (amd64) and ARM (arm64) servers, also mixed in one cluster.
- Works without internet, with an offline bundle.

## Requirements

- **Servers** with Ubuntu 24.04 or 26.04. They can be Intel/AMD (amd64) or ARM (arm64);
  the installer finds out which. Online, you can mix both types. An offline bundle works for one type only.
- **At least 2 CPUs and 4 GB of memory** on each server (a server for monitoring needs 2 GB more).
- **SSH login with a key**, and a user that can use `sudo` without a password.
- **A computer to run the installer**, with Python 3.12 or newer: your laptop (macOS or Linux),
  or the first manager server. It logs in to every server with SSH. It uses the server's `host`
  address, or its `ip` if `host` is not set.
- **Internet** on the servers and on that computer (it downloads Ansible from PyPI and Ansible Galaxy),
  or an [offline bundle](#offline-install).
- **A domain**, for HTTPS with Let's Encrypt (`tls: letsencrypt`): DNS for `*.<domain>` must already point
  to the public IP of the first manager.

Two things used everywhere below:
- Text in `<...>`, like `<domain>`, means: put your own value here (for example `example.com`).
- **The first manager** is the first server with `role: manager` in the `nodes:` list of `config.yml`.

## Quick start

First time? Follow [Getting started](docs/getting-started.md) instead. It shows every step.

```bash
git clone https://github.com/sgnd/ansibro.git
cd ansibro
cp config.example.yml config.yml   # edit: servers, ssh key, domain, apps
./install.sh
```

Point DNS for `*.<domain>` to the public IP of the first manager **before** you run it, so
Let's Encrypt can check the domain. Did you set DNS later? Then log in to the first manager
(`ssh <user>@<its IP>`) and run `sudo docker service update --force traefik_traefik`.
It asks Let's Encrypt for the certificates again.

At the end it prints how to reach each app, and saves it with all passwords in `state/summary.md`.

Run `./install.sh` again any time. It changes what is different in `config.yml`
(removing apps or servers is done by hand, see [How to](#how-to)).

> **Back up the `state/` folder.** It holds all generated passwords. If you lose it,
> the next run makes new passwords that do not match your running databases.
> Always run the installer from the same machine, or copy `state/` with it.
> See [Keep `state/` safe](#how-to).

## Examples

**One server.** Everything on one machine. `ip` is the private IP, `host` the public IP where the
installer connects (no private IP? Use the public IP for both):

```yaml
nodes:
  - { name: server1, ip: 10.0.0.10, host: 203.0.113.10, role: manager }
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

Pick one per category. In `config.yml`, a [swarm app](docs/getting-started.md#words) gets `swarm` (for example `traefik: swarm`).
A server app gets the name of the server it runs on (for example `postgres: server1`);
it runs there with [Docker Compose](docs/getting-started.md#words).
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
| secrets | [openbao](https://openbao.org) | server | 8200 | `openbao.<domain>` |
| observability (metrics, logs, alerts) | [prometheus](https://prometheus.io) (+ Loki) / [victoria](https://victoriametrics.com) (VictoriaMetrics + VictoriaLogs), both with Alertmanager and Grafana | server | | `grafana.<domain>`, `alertmanager.<domain>`, `metrics.<domain>` (+ `logs.<domain>` for victoria) |

Users and password files are listed in [`catalog.yml`](catalog.yml), and printed at the end of
the install. Passwords are in `state/secrets/`, and all together in `state/summary.md`.

Some apps need others:
- Every app with a web page needs traefik. (rabbitmq, nats and rustfs work without it, but then have no web page.)
- kong needs postgres. keycloak needs a database. authelia needs a database and a cache.
  The installer creates their databases for them.

Swarmpit and Uptime Kuma create their admin user on the first visit. So their pages first ask for
the Traefik dashboard login (user `admin`, password in `state/secrets/traefik_admin`); after that you
create the app's own admin user.

**With Authelia, admin pages use Authelia.** The Traefik dashboard, Swarmpit, Uptime Kuma, Kong
Manager, Alertmanager and the other pages that ask for the Traefik login then ask for the Authelia
login instead (user `admin`, password in `state/secrets/authelia_admin`), with a second factor (an
authenticator app). The first time, Authelia asks for a code that it writes to
`/opt/ansibro/authelia/config/notification.txt` on the first manager.

**OpenBao** keeps secrets for your apps. Log in at `https://openbao.<domain>` with the root token
(`state/secrets/openbao_root_token`), and make a token or user with a policy for each app; apps read
secrets from `http://<server ip>:8200/v1/secret/data/<path>`. OpenBao starts sealed (locked: it gives out
no secrets) after a restart:
run `./install.sh` again (it unseals it with `state/secrets/openbao_unseal_key`), or unseal it on
the web page. With monitoring, the alert `OpenBaoSealed` tells you.

## How to

Commands that start with `sudo` run on a server: log in first with `ssh <user>@<server IP>`.
They need `sudo` because the passwords and data in `/opt/ansibro/` are readable by root only.
Commands that start with `./install.sh` run on your computer, in the ansibro folder.

**Keep `state/` safe and encrypted.** The `state/` folder holds every password the installer made.
Keep a copy outside the cluster. To keep it encrypted, install [age](https://age-encryption.org)
(`brew install age` on a Mac, `sudo apt install age` on Ubuntu), then make a key once, on the computer
that runs the installer. Keep a copy of the key somewhere safe (a password manager):

```bash
# on your computer
mkdir -p ~/.config/ansibro && age-keygen -o ~/.config/ansibro/age.key
```

From then on `state/` is kept as `state.age`, encrypted.
`./install.sh` opens it while it runs and closes it at the end. To read a password:
`scripts/state.sh open`, and `scripts/state.sh close` when you are done.

**Back up and restore.** Add `backup:` to `config.yml` (see [`config.example.yml`](config.example.yml))
and run `./install.sh`. Every server then backs up each night with [restic](https://restic.net)
(encrypted), and the install runs the first backup right away. What is saved:

- databases (PostgreSQL, MariaDB) as a dump (one file with all the data), while they run
- every other folder in `/opt/ansibro/`: the app is paused for a moment while its files are copied
- RustFS and Garage data as it is, while it runs
- on the first manager: the swarm (your stacks, secrets, configs, networks), `config.yml` and `state/`

Not saved: the image registry (the installer fills it again; push your own images again)
and Docker volumes. Keep your own stacks' files in `/opt/ansibro/<stack name>/` so they are saved too:
their containers are paused while copied, like the apps above.

```bash
# on a server, after ssh
sudo ansibro-backup              # back up now
sudo ansibro-backup snapshots    # list the backups
```

To move the cluster to new servers, or after you lost it: make new servers, keep the same node names
and `ip` values (with `wireguard: true` only `host` changes), keep `state/`, and run:

```bash
# on your computer, in the ansibro folder
./install.sh -e restore=true
```

(`-e name=value` gives the installer an extra option.)

Each server gets its newest backup back, the swarm comes back with your stacks, and the databases are
loaded from their dumps. Old servers are removed from the swarm. A restore only runs on new servers.
If you lost `state/` too, get it back from the backup. You need the restic password (`state/secrets/restic`;
keep a copy of it outside the cluster). Install [restic](https://restic.net) on your computer, then run
this, with `<repository>` the `backup.repository` from `config.yml`:
`restic -r <repository> restore latest --host <first manager name> --include /opt/ansibro/backup/stage/installer --target .`

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
Grafana has an "Ansibro overview" dashboard. Logs: Grafana > Explore (prometheus), or
`https://logs.<domain>/select/vmui` (victoria).

**Who watches the monitoring?** If the monitoring server stops, it cannot send an alert. So there is a
test alert, `Watchdog`, that is always on. Something on another server checks that it is still there.
If it is gone, the monitoring is broken:

- Uptime Kuma (put `uptimekuma` on another server): add a monitor of type "HTTP(s) - Keyword",
  URL `http://<monitoring server ip>:9093/api/v2/alerts?filter=alertname=Watchdog`, keyword `Watchdog`.
  The install prints this URL. When the monitoring server, Alertmanager or the alert rules stop,
  the keyword is gone and Uptime Kuma tells you. The monitoring server sends an alert when Uptime Kuma's
  server is down, so the two watch each other.
- Or a heartbeat service outside the cluster, like [healthchecks.io](https://healthchecks.io): put its URL
  in `monitoring.heartbeat_url`. Alertmanager sends it a POST about every 2 minutes; set its period to 5 minutes.
  (Uptime Kuma's "Push" monitor does not work here: it takes only GET.)

**Remove an app.** Remove it from `config.yml` and run `./install.sh`. The installer stops it
(and its agents, Traefik page and timer). Its data stays in `/opt/ansibro/<app>` on its server:
`sudo rm -rf /opt/ansibro/<app>` if you do not need it. Not removed by itself: the app's database
(drop it in Postgres or MariaDB) and its old images in the registry.

**Remove a server.** Move its server apps to other servers first, then remove it from `config.yml`
and run `./install.sh -e remove_nodes=true`. The installer takes it out of the swarm (a manager is
demoted first) and the other servers' firewalls forget it. Without `-e remove_nodes=true` the
installer stops and lists the servers it would remove, so a typo cannot remove one.
Then turn the server off. Never remove the first manager.

**Add a server.** Add it to `config.yml`, after the first manager, and run `./install.sh`.

**Change a server's role** (worker to manager or back). The installer does not do this; it stops and
shows the command: `sudo docker node promote <name>` or `sudo docker node demote <name>` on a manager.

**Upgrade an app.** Change its tag (the version name) and digest (a fingerprint of that exact image)
in `versions.yml`, then run `./install.sh`.
Big Postgres upgrades (for example 18 to 19) need a dump (one file with all the data) and a restore by hand.
A new Docker version is installed one server at a time, so the swarm keeps running.

**Database replicas.** Give PostgreSQL a list of servers: `postgres: [db1, db2]`. The first is
the primary; apps use it. The others are replicas: read-only copies that follow it all the time
(alert `PostgresReplicaBehind` if one falls behind). If the primary dies, make a replica the new primary:

```bash
sudo docker exec -u postgres postgres pg_ctl promote -D /var/lib/postgresql/18/docker   # on the replica
```

Then put that server first in the list, take the old primary out of it (delete its
`/opt/ansibro/postgres` folder before you add it back, so it comes back as a replica), and run
`./install.sh` so the apps use the new primary. This is not automatic yet.

**Garage on 3 servers.** `garage: [s1, s2, s3]` keeps every file on all 3 servers, so one can
go down. Set it on the first install: the number of copies cannot change later.

## Check that everything works

After an install, check every app for real (logins, databases, S3 keys, web pages).
Run it on the computer where you ran `./install.sh`, in the same folder:

```bash
.venv/bin/python tests/check.py          # or: .venv/bin/python tests/check.py other.yml
```

It prints PASS or FAIL for each check. The checks run on the first manager
(over SSH if you are on another machine), because the firewall only lets cluster servers reach the apps.

## Troubleshooting

Commands that start with `sudo` run on a server: log in first with `ssh <user>@<server IP>`.

| Problem | Try |
|---------|-----|
| `UNREACHABLE`, `Permission denied (publickey)` or `Missing sudo password` | Check that you can log in yourself: `ssh <user>@<host>`. Check `ssh.user`, `ssh.key` and each node's `host` in `config.yml`, and that port 22 is open in your cloud firewall. The user must use `sudo` without a password. |
| `command not found: python3` or `Python 3.12 or newer is needed` | Install Python: `brew install python@3.12` on a Mac ([brew.sh](https://brew.sh) if you have no `brew`), `sudo apt install python3 python3-venv` on Ubuntu. |
| `config error: ...` | The message says what to fix in `config.yml`. |
| Locked out of SSH | Check `ssh.allow_from`. Use your provider's console to run `sudo ufw disable`. |
| `cannot reach ... over WireGuard` | Open UDP 51820 between the servers' `host` addresses in your cloud firewall. `sudo wg show` shows the last handshake. |
| No HTTPS certificate | DNS must point to the server Traefik runs on (with `tls: letsencrypt`: the first manager), and port 80 must be open. Then run `sudo docker service update --force traefik_traefik` on the first manager. Let's Encrypt has rate limits. |
| App not starting | Swarm apps: `sudo docker service ls`, `sudo docker service logs <stack>_<service>`. Server apps: `sudo docker ps`, `sudo docker logs <app>`. |
| `no such host` or a timeout while downloading | A network problem on the server. Check its internet, then run `./install.sh` again. It is safe to run again: it continues where it stopped. |
| No alerts arrive | Look at `https://alertmanager.<domain>`: if alerts are there, check `monitoring:` in `config.yml` and the `AlertsNotSent` alert. Logs: `sudo docker logs alertmanager` on the monitoring server. |
| An alert you do not want | Silence it in `https://alertmanager.<domain>` (for a time), or change the rule in `roles/observability/files/alerts.yml`. |
| `toomanyrequests` from Docker Hub | Docker Hub limits pulls. Wait, or run `sudo docker login` on the first manager. |

## Offline install

For servers with no internet (for example only VPN access).

**1. Get a bundle.** Each release on GitHub has them, for both CPU types and Ubuntu versions.
They come in parts (GitHub allows 2 GB per file); put the parts back together and check them:

```bash
cat ansibro-24.04-amd64.tar.gz.part* > ansibro-24.04-amd64.tar.gz
sha256sum -c ansibro-24.04-amd64.tar.gz.sha256   # on a Mac: shasum -a 256 -c ...
```

Or build one yourself: **on a machine with internet and Docker**, build a bundle for the CPU and Ubuntu version
of your servers. A Mac (Docker Desktop or OrbStack) can build both CPU types. On Linux,
building for the other CPU type needs QEMU, which lets one CPU type run programs for the other.
This command installs it: `docker run --privileged --rm tonistiigi/binfmt --install all`.

```bash
./build-bundle.sh amd64          # Intel/AMD servers, Ubuntu 24.04
./build-bundle.sh arm64 26.04    # ARM servers, Ubuntu 26.04
```

This makes `dist/ansibro-<ubuntu>-<arch>.tar.gz` (about 2.5 GB). It holds this project, apt packages,
Ansible and all Docker images from `versions.yml`. Your project folder is not changed.

**2. Copy it to the first manager**, together with your SSH private key and, if you use them,
your `tls_cert`/`tls_key`/`acme_ca_cert` files (the bundle leaves out keys and certificates).
The installer connects over SSH to every server, the first manager itself too, so that key must
be allowed on all servers. Then run the installer there:

```bash
tar -xzf ansibro-24.04-amd64.tar.gz
cd ansibro
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

## Docker Swarm or k3s

`orchestrator: swarm` (the default) or `orchestrator: k3s` in `config.yml`. Everything around the
cluster is the same: firewall, WireGuard, registry, server apps (databases, storage, monitoring...),
backup, monitoring and alerts, offline bundle.

With k3s:
- Managers are k3s servers (3 managers = the cluster survives one down), workers are k3s agents.
  Standalone servers run server apps and are not in the cluster. The pinned k3s version is in `versions.yml`.
- Use `kubectl` on a manager: `sudo k3s kubectl get nodes`. To use it from your laptop, copy
  `/etc/rancher/k3s/k3s.yaml` from a manager and change `127.0.0.1` in it to the manager's address.
- Traefik is k3s's built-in one: `traefik: cluster` in `apps`. Server apps get their web pages through it
  like with Swarm. Point DNS to any cluster server. Your own apps: an `Ingress` or Traefik `IngressRoute`.
- Pods pull from the cluster's registry: `registry.ansibro:5000/<image>:<tag>` (push your images there).
- For now these apps are Swarm only: kong, portainer, swarmpit, keycloak, authelia.
- The backup has a k3s (etcd) snapshot. `-e restore=true` is Swarm only for now; to restore k3s, see
  [k3s backup and restore](https://docs.k3s.io/datastore/backup-restore).

## Advanced

You do not need this for a normal install.

**More installer options.** Extra `ansible-playbook` options go after the config file,
for example `./install.sh config.yml -v` (more output). Check mode (`--check`) is not supported.

**GPU servers.** Set `gpu: true` on a server with an NVIDIA GPU. The installer installs the
NVIDIA driver that Ubuntu recommends (and restarts the server once), the NVIDIA Container Toolkit,
and makes `nvidia` Docker's default runtime there. Swarm servers get the label `gpu=true`. A service
that needs the GPU:

```yaml
    environment:
      NVIDIA_VISIBLE_DEVICES: all
    deploy:
      placement:
        constraints: [node.labels.gpu == true]
```

With monitoring, dcgm-exporter reports GPU use, temperature and memory (alerts `GpuTooHot`,
`GpuErrors`, `GpuMemoryFull`). GPU servers need internet. If the installer runs on a GPU server,
restart it by hand after the first run and run `./install.sh` again. The NVIDIA driver is not
open source; it is only installed with `gpu: true`.

**Kong.** Kong runs on its own network, `kong`, shared only with Traefik. Put your API services on that
network too (`networks: [kong]`, external) so Kong can reach them. Other apps cannot reach Kong's admin API.

**Swarmpit.** Swarmpit needs CouchDB 2.3 and InfluxDB 1.8, which are old. They are only on Swarmpit's own
network, but if you want only up-to-date software, choose Portainer.

**Authelia login in front of an app.** Add `authelia@file` to the app's Traefik middlewares:
for a swarm app in `roles/<app>/templates/stack.yml.j2` (the `...middlewares` label, comma-separated),
for a server app with a web page set `traefik_route_middleware: authelia@file` in `roles/<app>/tasks/main.yml`.
A server app has one middleware, so this replaces its `admin_allow_from` limit.

## How it works

`install.sh` installs Ansible into `.venv/`, reads `config.yml` through
[`inventory.py`](inventory.py) (which also checks it), and runs [`site.yml`](site.yml):

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

### Firewall

| Open | To |
|------|----|
| SSH | `ssh.allow_from`, or anyone |
| 80, 443 | anyone, on swarm servers |
| the ports a server needs: swarm, registry, its apps, monitoring agents | other servers in `config.yml` (from their `ip`) |
| UDP 51820 | other servers' `host`, with `wireguard: true` |
| everything | containers on the same server (`docker0`, `docker_gwbridge`) |
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

### Good to know

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

## Contributing

Rules: keep it simple, a beginner must be able to read every file. Use simple English.
Only open-source apps, every version pinned.

How to suggest or add an app, run the checks and send a pull request: see [CONTRIBUTING.md](CONTRIBUTING.md).
This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE). The apps it installs have their own licenses, see [THIRD_PARTY.md](THIRD_PARTY.md).
Changes: see [CHANGELOG.md](CHANGELOG.md).
Security issues: see [SECURITY.md](SECURITY.md).
