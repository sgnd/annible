# swarm

Set up a production-ready Docker Swarm with one command.

- Works on 1 server or many.
- You pick the apps and where they run.
- All versions are pinned in [`versions.yml`](versions.yml). Nothing uses `latest`.
- Only open-source apps.

## Requirements

- Ubuntu 24.04 or newer on every server, amd64 (Intel/AMD) or arm64
- SSH key login with passwordless sudo
- Python 3 on the machine that runs the installer (a server or your laptop)

## Quick start

```bash
git clone https://github.com/sgnd/swarm.git
cd swarm
cp config.example.yml config.yml   # edit: servers, ssh key, domain, apps
./install.sh
```

At the end it prints the app URLs. Passwords are saved in `state/secrets/`.

Run `./install.sh` again any time. It only changes what is different.
To add a server, add it to `config.yml` and run it again.

## Config

Everything is in [`config.yml`](config.example.yml).

**Servers** have one of three roles:

| Role | What it does |
|------|--------------|
| `manager` | Runs the swarm. Use 1, 3 or 5. |
| `worker` | Runs swarm apps. |
| `standalone` | Not in the swarm. Runs apps like databases with Docker Compose. |

**Apps** say where each app runs. Apps not listed are not installed.

```yaml
apps:
  traefik: swarm       # run as a swarm service
  portainer: swarm
  # postgres: data1    # run on the server named data1 (coming soon)
```

## Apps

| App | Category | Status |
|-----|----------|--------|
| traefik | gateway (HTTPS, routing) | ready |
| portainer | management UI | ready |
| kong, swarmpit, postgres, mariadb, redis, valkey, rustfs, garage, rabbitmq, nats, keycloak, authelia, uptimekuma, beszel | | coming soon |

Only one app per category. The list lives in [`catalog.yml`](catalog.yml).

## How it works

`install.sh` reads `config.yml` and runs [`site.yml`](site.yml), in this order:

1. **common**: hostname, packages, time sync, firewall
2. **docker**: installs Docker
3. **registry**: local image registry on the first manager
4. **swarm**: creates the swarm and joins the servers
5. **apps**: one role per app, in `roles/<app>/`

Firewall: SSH is open (or only `ssh.allow_from`), 80 and 443 are open on swarm servers,
and servers in the cluster can reach each other. Everything else is blocked.

## Add a new app

1. Add it to `catalog.yml`.
2. Add its image to `versions.yml` (tag + multi-arch digest).
3. Copy `roles/portainer/` to `roles/<app>/` and edit:
   - `defaults/main.yml`: settings and passwords
   - `templates/stack.yml.j2`: the Docker stack file
   - `tasks/main.yml`: create folders, mirror the image, deploy
4. Add it to `apps:` in your `config.yml` and run `./install.sh`.

## License

[MIT](LICENSE)
