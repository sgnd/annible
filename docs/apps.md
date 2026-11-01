# Apps: logins and notes

Where the passwords are, what each app needs, and notes for some apps. The list of apps is in the [README](../README.md#apps).

Users and password files are listed in [`catalog.yml`](../catalog.yml), and printed at the end of
the install. Passwords are in `state/secrets/`, and all together in `state/summary.md`.

Some apps need others:
- Every app with a web page needs traefik. (rabbitmq, nats and rustfs work without it, but then have no web page.)
- kong needs postgres. keycloak needs a database. authelia needs a database and a cache.
  The installer creates their databases for them.

Swarmpit and Uptime Kuma create their admin user on the first visit. So their pages first ask for
the Traefik dashboard login (user `admin`, password in `state/secrets/traefik_admin`); after that you
create the app's own admin user.

**With Authelia, admin pages use Authelia.** The Traefik dashboard, Swarmpit, Uptime Kuma, Kong
Manager, Alertmanager and the other pages that ask for the Traefik login then ask for the Authelia
login instead (user `admin`, password in `state/secrets/authelia_admin`), with a second factor (an
authenticator app). The first time, Authelia asks for a code that it writes to
`/opt/ansibro/authelia/config/notification.txt` on the first manager.

**OpenBao** keeps secrets for your apps. Log in at `https://openbao.<domain>` with the root token
(`state/secrets/openbao_root_token`), and make a token or user with a policy for each app; apps read
secrets from `http://<server ip>:8200/v1/secret/data/<path>`. OpenBao starts sealed (locked: it gives out
no secrets) after a restart:
run `./install.sh` again (it unseals it with `state/secrets/openbao_unseal_key`), or unseal it on
the web page. With monitoring, the alert `OpenBaoSealed` tells you.
