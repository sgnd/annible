# Plan

## Done

- Base setup: OS, firewall, Docker, local registry, swarm
- `apps:` config: choose apps and where they run
- traefik, portainer

## Next

1. Standalone apps with Docker Compose: postgres/mariadb, redis/valkey, rustfs/garage, rabbitmq/nats
2. Offline install: `build-bundle.sh` makes one file with all packages and images for the target `arch`
3. Swarm apps: kong, swarmpit, keycloak/authelia, uptimekuma/beszel

## Rules

- Simple and easy to read. A beginner should be able to change it.
- Simple English.
- Open-source apps only. Two choices per category, the popular one first.
- Pin every version. No `latest`.
- Swarm runs stateless apps. Data lives on standalone servers.
