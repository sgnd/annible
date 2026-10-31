# Changelog

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
