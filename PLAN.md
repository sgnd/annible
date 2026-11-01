# Plan

## Done

- Base setup: OS, firewall, Docker, local registry, swarm
- `apps:` config: choose apps and the server they run on
- Swarm apps: traefik, kong, portainer, swarmpit, keycloak, authelia
- Server apps: postgres, mariadb, redis, valkey, rustfs, garage, rabbitmq, nats, uptimekuma, beszel
- Offline install: `build-bundle.sh` makes one file with apt packages, Ansible and images
- `host` per node (multi-IP servers), optional WireGuard network, swarm MTU, cloud-init hostname
- Backup (restic, nightly) and restore of the whole cluster on new servers

## Next

1. Monitoring and alerts for every server and app
2. HA: Traefik on all managers, a second registry, `tier=app` / `tier=data` labels
3. Database HA (Postgres replica and failover, Garage on 3 servers, ...)
4. Zero trust: encrypt `state/` (sops + age), SSO for admin pages, firewall per app, image scan in CI
5. Secrets: OpenBao or Infisical
6. Remove apps and nodes automatically (today: by hand, see README)
7. Release bundles on GitHub (build in CI on each tag)

## Rules

- Simple and easy to read. A beginner should be able to change it.
- Simple English.
- Open-source apps only. At most two choices per category, the popular one first.
- Pin every version. No `latest`.
- Databases, caches, storage, queues and monitoring run on one server with Docker Compose.
  Swarm apps that keep data (Traefik, Portainer, Swarmpit, Authelia) are pinned to the first manager.
