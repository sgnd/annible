# Apps: logins and notes

Where the passwords are, what each app needs, and notes for some apps. The list of apps is in the [README](../README.md#apps).

## Where the passwords are

All addresses, users and passwords are in `state/summary.md`. Each password is also a file in
`state/secrets/`. (If `state/` is encrypted: `scripts/state.sh open` first, `scripts/state.sh close` after.)
For developers: the list is in [`catalog.yml`](../catalog.yml).

## What each app needs

- Every app with a web page needs traefik. (rabbitmq, nats and rustfs work without it, but then have no web page.)
- kong needs postgres. keycloak needs a database. authelia needs a database and a cache.
  The installer creates their databases for them.

## Swarmpit and Uptime Kuma: first visit

Swarmpit and Uptime Kuma create their admin user on the first visit. So their pages first ask for
the Traefik dashboard login (user `admin`, password in `state/secrets/traefik_admin`); after that you
create the app's own admin user.

## With Authelia, admin pages use Authelia

When you install Authelia, the Traefik dashboard, Swarmpit, Uptime Kuma, Kong Manager, Alertmanager
and the other pages that ask for the Traefik login ask for the Authelia login instead (user `admin`, password in `state/secrets/authelia_admin`), with a second factor (an
authenticator app). The first time, Authelia asks for a code that it writes to
`/opt/ansibro/authelia/config/notification.txt` on the first manager.

## OpenBao

OpenBao keeps secrets (passwords, API keys) for your apps. Log in at `https://openbao.<domain>` with the
root token, the admin password (`state/secrets/openbao_root_token`). For each app, make a token or a user
with a policy (the list of secrets it may read). Apps read secrets from
`http://<server ip>:8200/v1/secret/data/<path>`.

After a restart, OpenBao is sealed (locked: it gives out no secrets). To unseal it,
run `./install.sh` again (it unseals it with `state/secrets/openbao_unseal_key`), or unseal it on
the web page. With monitoring, the alert `OpenBaoSealed` tells you.
