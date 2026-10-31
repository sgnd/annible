# Plan

## Done

- Base setup: OS, firewall, Docker, local registry, swarm
- `apps:` config: choose apps and the server they run on
- Swarm apps: traefik, kong, portainer, swarmpit, keycloak, authelia
- Server apps: postgres, mariadb, redis, valkey, rustfs, garage, rabbitmq, nats, uptimekuma, beszel
- Offline install: `build-bundle.sh` makes one file with apt packages, Ansible and images

## Next

1. Remove apps and nodes automatically (today: by hand, see README)
2. Optional WireGuard for servers that only have public IPs
3. Release bundles on GitHub (build in CI on each tag)

## Rules

- Simple and easy to read. A beginner should be able to change it.
- Simple English.
- Open-source apps only. Two choices per category, the popular one first.
- Pin every version. No `latest`.
- Swarm apps are stateless. Apps with data run on one server with Docker Compose.
