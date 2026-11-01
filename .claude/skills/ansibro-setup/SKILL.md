---
name: ansibro-setup
description: Write config.yml for Ansibro with the user. Use when someone wants to set up a new swarm, pick apps, or change servers or apps in config.yml.
---

# Set up config.yml

Goal: a valid `config.yml`. Start from `config.example.yml`. Every setting is explained there.

## Ask the user

Ask only what you cannot guess. Keep it short.

1. **Cluster**: Docker Swarm (default) or k3s (`orchestrator: k3s`). On k3s, kong, portainer,
   swarmpit, keycloak and authelia are not available yet; traefik is written `traefik: cluster`.
2. **Servers**: name, private IP, role for each one.
   - `manager` runs the cluster (swarm manager or k3s server). Use 1, 3 or 5.
   - `worker` runs cluster apps (swarm worker or k3s agent).
   - `standalone` is not in the cluster. Good for databases and storage.
   - One server only? Make it a `manager` and put every app on it.
   - `gpu: true` for a server with an NVIDIA GPU (needs internet).
3. **CPU** of the servers (not the laptop): `amd64` or `arm64`. The installer finds it; they may mix
   with internet. The offline bundle needs one CPU type. **Ubuntu** must be 24.04 or 26.04.
4. **Domain** for the web pages, for example `example.com`.
5. **Internet on the servers?**
   - Yes: `tls: letsencrypt` and set `acme_email`. DNS must point to the first manager **before** the install.
   - No: `tls: selfsigned`, `custom` (their own wildcard cert), or `letsencrypt` with `acme_server`
     set to an ACME server in their network (plus `acme_ca_cert` if its certificate is private).
     Then use the `ansibro-install` skill for the offline bundle.
6. **SSH**: user (needs passwordless sudo), key path, port. Ask if SSH should be limited to some IPs (`ssh.allow_from`).
7. **Apps**: which ones and where. See the rules below.

## App rules

All apps are in `catalog.yml`.

- One app per `category`. For example postgres **or** mariadb, not both.
- `runs_on: swarm` apps get the value `swarm` (or `cluster`, the same; nicer with k3s).
- postgres can have replicas: `postgres: [db1, db2]`. garage on 3 servers: `garage: [s1, s2, s3]`.
- `runs_on: node` apps get a server name. Put them on a `standalone` server if there is one.
- Check `requires`. For example kong needs postgres and traefik. `database` means postgres or mariadb.
- Apps with a web page need `traefik`.
- If they don't say, pick the popular one (the first one in each category).

## Check it

```bash
ANSIBRO_CONFIG=config.yml .venv/bin/python inventory.py --list > /dev/null   # or: python3 inventory.py --list
```

No output means the config is fine. If you get `config error: ...`, the message says what to fix.
No `.venv/` yet? Use `python3` (needs PyYAML), or let the first `./install.sh` do the check.
If a `bundle/` folder is here, the check treats it as an offline install.

## Tell the user

- Point DNS for `*.<domain>` to the **public** IP of the first manager, before the install.
- The firewall is owned by the installer: other open ports (for example a VPN) must be in `firewall_allow`,
  or they are closed. Server IPs must be outside `10.200.0.0/16` (swarm) and `10.42.0.0/16`, `10.43.0.0/16` (k3s).
- Keep the first manager first in `nodes`; add new servers after it.
- The `ip` of each node is its **private** IP. If the installer must SSH to another address (a public IP),
  put that in `host`. With `wireguard: true`, every node needs `host`, and `ip` is a new WireGuard address
  (for example 10.99.0.11); open UDP 51820 between the hosts in the cloud firewall.
- Suggest `backup:` with storage outside the cluster (S3 or rest-server). The restic password is in
  `state/secrets/restic`: keep `state/` safe outside the cluster. Restore on new servers: `./install.sh -e restore=true`.
- Suggest monitoring: `victoria` (lighter) or `prometheus` on a server with 2 GB free memory, plus `monitoring:`
  with at least one of telegram, email or webhook. Put `uptimekuma` on another server and, after the first
  install, add the "HTTP(s) - Keyword" monitor the install prints, so someone watches the monitoring server.
- Next step: run the installer (skill `ansibro-install`).
