# Plan

## Done

- Base setup: OS, firewall, Docker, local registry, swarm
- `apps:` config: choose apps and the server they run on
- Swarm apps: traefik, kong, portainer, swarmpit, keycloak, authelia
- Server apps: postgres, mariadb, redis, valkey, rustfs, garage, rabbitmq, nats, uptimekuma, beszel,
  prometheus, victoria, openbao
- Offline install: `build-bundle.sh` makes one file with apt packages, Ansible and images
- `host` per node (multi-IP servers), optional WireGuard network, swarm MTU, cloud-init hostname
- Backup (restic, nightly) and restore of the whole cluster on new servers
- Monitoring and alerts: prometheus or victoria, agents on every server, Uptime Kuma watches the monitoring server
- HA: registry and Traefik on every manager, tier labels
- PostgreSQL replicas (manual failover), Garage on 3 servers
- Zero trust: per-port firewall between servers, Authelia (2FA) for admin pages, encrypted `state/`, image scan in CI
- Secrets: OpenBao
- Admin pages behind Authelia or Keycloak (both with a second factor)
- Remove apps and servers that are no longer in `config.yml`
- Offline bundles built in CI for each release
- GPU servers (NVIDIA)
- k3s as a second orchestrator (`orchestrator: k3s`), with portainer, kong, keycloak, authelia and restore

## Next

1. Test everything above on real servers (DigitalOcean), see "Not tested yet" in CHANGELOG
2. Automatic PostgreSQL failover (Patroni), MariaDB and Valkey replicas

## Rules

- Simple and easy to read. A beginner should be able to change it.
- Simple English.
- Open-source apps only. At most two choices per category, the popular one first.
- Pin every version. No `latest`.
- Databases, caches, storage, queues and monitoring run on one server with Docker Compose.
  Swarm apps that keep data (Traefik, Portainer, Swarmpit, Authelia) are pinned to the first manager.
