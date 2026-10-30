# swarm

Ansible installer for a production-ready Docker Swarm. Single or multi node, one command.

- **Swarm (1+N nodes)** — stateless services: gateway, management, auth, your apps.
- **Data server (optional)** — stateful services with Docker Compose.
- **Local registry** — every node pulls images from it.
- **Pinned versions** — see [`versions.yml`](versions.yml). Nothing uses `latest`.

## Requirements

- Ubuntu 24.04 or newer on every node, amd64 (Intel/AMD) or arm64 (Apple silicon VMs, Graviton, Ampere)
- SSH key access with passwordless sudo
- Python 3 on the machine running the installer (first manager, or a Linux/macOS workstation)

## Usage

```bash
cp config.example.yml config.yml   # set nodes, ssh key, apps
./install.sh                       # or: ./install.sh path/to/config.yml
```

Run it again any time: it is idempotent. Add a node to `config.yml` and rerun to join it.

Extra arguments go to `ansible-playbook`, e.g. `./install.sh config.yml --check`.

## Firewall

| Port | Open to |
|------|---------|
| SSH | `ssh.allow_from`, or anywhere |
| 80, 443 | anywhere (swarm nodes) |
| 2377, 7946, 4789 | other swarm nodes |
| 5000 (registry) | all nodes |

## Catalog

| Category   | Default    | Alternative |
|------------|------------|-------------|
| gateway    | traefik    | kong        |
| management | portainer  | swarmpit    |
| database   | postgres   | mariadb     |
| cache      | redis      | valkey      |
| storage    | rustfs     | garage      |
| queue      | rabbitmq   | nats        |
| auth       | keycloak   | authelia    |
| monitoring | uptimekuma | beszel      |

Work in progress, see [PLAN.md](PLAN.md). Currently implemented: base system, Docker, registry, swarm.

## License

[MIT](LICENSE)
