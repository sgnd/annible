---
name: annible-setup
description: Write config.yml for Annible with the user. Use when someone wants to set up a new swarm, pick apps, or change servers or apps in config.yml.
---

# Set up config.yml

Goal: a valid `config.yml`. Start from `config.example.yml`. Every setting is explained there.

## Ask the user

Ask only what you cannot guess. Keep it short.

1. **Servers**: name, private IP, role for each one.
   - `manager` runs the swarm. Use 1, 3 or 5.
   - `worker` runs swarm apps.
   - `standalone` is not in the swarm. Good for databases and storage.
   - One server only? Make it a `manager` and put every app on it.
2. **CPU** of the servers (not the laptop): `amd64` or `arm64`.
3. **Domain** for the web pages, for example `example.com`.
4. **Internet on the servers?**
   - Yes: `tls: letsencrypt` and set `acme_email`.
   - No: `tls: selfsigned` (or `custom` with their own wildcard cert). Then use the `annible-install` skill for the offline bundle.
5. **SSH**: user (needs passwordless sudo), key path, port. Ask if SSH should be limited to some IPs (`ssh.allow_from`).
6. **Apps**: which ones and where. See the rules below.

## App rules

All apps are in `catalog.yml`.

- One app per `category`. For example postgres **or** mariadb, not both.
- `runs_on: swarm` apps get the value `swarm`.
- `runs_on: node` apps get a server name. Put them on a `standalone` server if there is one.
- Check `requires`. For example kong needs postgres and traefik. `database` means postgres or mariadb.
- Apps with a web page need `traefik`.
- If they don't say, pick the popular one (the first one in each category).

## Check it

```bash
ANNIBLE_CONFIG=config.yml .venv/bin/python inventory.py --list > /dev/null
```

No output means the config is fine. If you get `config error: ...`, the message says what to fix.
No `.venv/` yet? Use `python3` (needs PyYAML), or let the first `./install.sh` do the check.
If a `bundle/` folder is here, the check treats it as an offline install.

## Tell the user

- Point DNS for `*.<domain>` to the **public** IP of the first manager.
- The `ip` of each node is its **private** IP.
- Next step: run the installer (skill `annible-install`).
