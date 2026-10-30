# Plan

## Done

- Base setup: OS, firewall, Docker, local registry, swarm
- `apps:` config: choose apps and the server they run on
- Swarm apps: traefik, portainer
- Server apps: postgres, mariadb, redis, valkey, rustfs, garage, rabbitmq, nats

## Next

1. Offline install: `build-bundle.sh` makes one file with all packages, images and Ansible
   for the target `arch`. Then servers need no internet.
2. Swarm apps: kong, swarmpit, keycloak/authelia, uptimekuma/beszel
3. Remove apps and nodes automatically (today: by hand, see README)
4. Optional WireGuard for servers that only have public IPs

## Rules

- Simple and easy to read. A beginner should be able to change it.
- Simple English.
- Open-source apps only. Two choices per category, the popular one first.
- Pin every version. No `latest`.
- Swarm apps are stateless. Apps with data run on one server with Docker Compose.
