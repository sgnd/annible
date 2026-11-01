# Changelog

## Unreleased

Annible is now called Ansibro: the repo is github.com/sgnd/ansibro, app files are in
`/opt/ansibro`, and the commands are `ansibro-backup` and `ansibro-metrics`.

Not tested yet (test before the next release):
- The rename to Ansibro on real servers (only the local checks ran).
- `prometheus` (Prometheus + Loki). `victoria` was tested on 3 arm64 servers: all checks, alerts
  by email and webhook, a second run with no changes.
- Mixed amd64 + arm64 clusters and the registry copy for both CPU types.
- Telegram alerts, RabbitMQ metrics, and a restore of a cluster with monitoring.
- HA: the registry on every manager, Traefik on every manager, tier labels.
- PostgreSQL replicas and Garage on 3 servers.
- Zero trust: the per-port firewall between servers, the Authelia login for admin pages,
  `state.age` encryption (only tried on a Mac), the image scan in CI.
- OpenBao.
- Removing apps and servers.
- The release workflow (bundles built by GitHub Actions on each tag).
- GPU servers (needs a server with an NVIDIA GPU).

New
- `gpu: true` on a node: NVIDIA driver, NVIDIA Container Toolkit (pinned), `nvidia` as Docker's
  default runtime, label `gpu=true`, and GPU monitoring with dcgm-exporter (3 GPU alerts).
- Each GitHub release gets the offline bundles for amd64 and arm64, Ubuntu 24.04 and 26.04,
  built by GitHub Actions (`.github/workflows/release.yml`).
- Remove an app: take it out of `config.yml` and run `./install.sh`. It stops (data kept).
- Remove a server: take it out of `config.yml` and run `./install.sh -e remove_nodes=true`.
  Without that option the installer stops and lists the servers it would remove.
- `openbao` app: secrets for your apps. The installer sets it up, saves the unseal key and root
  token in `state/secrets/`, unseals it on every run, and turns on `secret/` (KV version 2).
  Alert `OpenBaoSealed` when it needs unsealing after a restart.
- Zero trust:
  - Between your servers, only the ports in use are open (swarm, registry, each server's apps,
    monitoring agents). Before, servers could reach every port of each other.
  - With Authelia, every admin page uses the Authelia login with a second factor, instead of the
    Traefik password.
  - `state/` can be kept encrypted as `state.age` (with [age](https://age-encryption.org)):
    create a key in `~/.config/ansibro/age.key` and the installer does the rest. `scripts/state.sh`.
  - CI scans every pinned image for known security problems (`scripts/scan-images.sh`), each Monday.
- PostgreSQL replicas: `postgres: [db1, db2]`. The first server is the primary, the others follow
  it (streaming replication). Failover is one command (see README), not automatic yet.
- Garage on 3 servers: `garage: [s1, s2, s3]` keeps 3 copies of every file.
- HA: every manager runs the image registry with the same images (apps use the name
  `registry.ansibro`), so images can be pulled when a manager is down. Traefik runs on every
  manager, except with `tls: letsencrypt` (see README). Swarm servers get the label `tier=data`
  (they run server apps) or `tier=app`; Kong and Keycloak run on `tier=app` servers.
- Monitoring and alerts: `prometheus` (Prometheus + Loki) or `victoria` (VictoriaMetrics + VictoriaLogs),
  both with Alertmanager and Grafana. Agents on every server collect the server, its containers, all
  logs and the database stats. Alerts for servers, apps, containers, swarm services, disks, memory,
  clock, backups, WireGuard, certificates, databases and the monitoring itself, sent to Telegram,
  email or a webhook (`monitoring:` in `config.yml`). An always-firing `Watchdog` alert, checked by
  Uptime Kuma on another server (or a heartbeat service), tells you when the monitoring itself is down.
- `backup:` nightly backup of every server with restic (S3, rest-server or a mounted folder):
  database dumps, app folders (paused for a moment while copied), RustFS/Garage data, and on the
  first manager the swarm state, `config.yml` and `state/`. The install runs the first backup.
- `./install.sh -e restore=true`: put the newest backup back on new servers. The swarm comes back
  with your stacks, the databases are loaded from their dumps, and old servers leave the swarm.
- `host` per node: the address the installer connects to over SSH, when it is not the node's `ip`.
  For servers with more than one IP, like a public IP for SSH and a private IP for the cluster.
- `wireguard: true`: an encrypted WireGuard network between all servers. The swarm uses only the
  WireGuard addresses (`ip`), so a server's real address (`host`) can change.
- Swarm networks get the right MTU (smallest server MTU minus 50), so big requests do not hang on
  WireGuard or on clouds with a smaller network MTU. New networks only.
- The installer finds each server's CPU type itself; `arch:` in `config.yml` is now optional.
  With internet, amd64 and arm64 servers can be in one cluster: the local registry keeps every
  image for each CPU type in use.
- On cloud servers, cloud-init keeps the hostname and `/etc/hosts` after a reboot.
- The install stops with a clear message if a server's swarm address differs from its `ip` in `config.yml`
  (for example after a snapshot restore on a new IP).

Fixes
- With `wireguard: true` and the installer on one of the servers, the install could hang on new
  servers when the firewall or Docker started. The firewall now always lets SSH replies from the
  other servers in.
- The local registry kept only one CPU type of each image. It now copies the image for every
  CPU type in the cluster (`docker buildx imagetools`). The first manager trusts the registry
  certificate for this.

## 1.0.1

Fixes from a full independent review of 1.0.0. Upgrade: pull, then run `./install.sh` again.

Security
- Swarmpit and Uptime Kuma now ask for the Traefik dashboard login first. Before, anyone could
  open them and create the first admin user.
- The local registry needs a login. Every server logs in; Swarm passes the login to its tasks.
- Kong runs on its own `kong` network, so other apps cannot reach its admin API.
- Swarm join tokens, the Redis/Valkey password and the Garage key no longer show up in output or
  process lists.

Fixes
- Swarm networks use `10.200.0.0/16`, so servers on `10.0.0.x` work. (New swarms only.)
- A renewed custom TLS certificate is loaded (Traefik restarts).
- Docker upgrades run one server at a time.
- The install stops with a clear message, before it changes anything, if the first manager is not
  the one that made the swarm, or if a server's role in `config.yml` differs from the swarm.
- If one server fails a check, the whole install stops (not only that server).
- A mistake in `config.yml` stops `./install.sh` with an error. Before, it could end with "success"
  and do nothing.
- Stack deploys wait until a rolling update is finished.
- Kong restarts when its database password changes.
- Downloading an image (install and `build-bundle.sh`) tries again (3 times) after a network error.
- Database passwords are set on every run, so they always match `state/secrets/`.
- Kong `migrations finish` runs after the new Kong is up.
- The offline bundle only contains files committed to git.
- More config checks: `domain`, `nodes`, `labels`, `localhost`, `firewall_allow`.

New
- `firewall_allow` in `config.yml` for your own open ports (for example a VPN).

Other
- LICENSE names Annible, CI actions pinned to commits, `ansible-lint` pinned, this changelog.

## 1.0.0

First release.
