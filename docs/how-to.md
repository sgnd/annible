# How to

Keep your passwords safe, back up, add monitoring, and change your cluster.

Commands that start with `sudo` run on a server: log in first with `ssh <user>@<server IP>`.
They need `sudo` because the passwords and data in `/opt/ansibro/` are readable by root only.
Commands that start with `./install.sh` run on your computer, in the ansibro folder.

**Keep `state/` safe and encrypted.** The `state/` folder holds every password the installer made.
Keep a copy outside the cluster. To keep it encrypted, install [age](https://age-encryption.org)
(`brew install age` on a Mac, `sudo apt install age` on Ubuntu), then make a key once, on the computer
that runs the installer. Keep a copy of the key somewhere safe (a password manager):

```bash
# on your computer
mkdir -p ~/.config/ansibro && age-keygen -o ~/.config/ansibro/age.key
```

From then on `state/` is kept as `state.age`, encrypted.
`./install.sh` opens it while it runs and closes it at the end. To read a password:
`scripts/state.sh open`, and `scripts/state.sh close` when you are done.

**Back up and restore.** Add `backup:` to `config.yml` (see [`config.example.yml`](../config.example.yml))
and run `./install.sh`. Every server then backs up each night with [restic](https://restic.net)
(encrypted), and the install runs the first backup right away. What is saved:

- databases (PostgreSQL, MariaDB) as a dump (one file with all the data), while they run
- every other folder in `/opt/ansibro/`: the app is paused for a moment while its files are copied
- RustFS and Garage data as it is, while it runs
- on the first manager: the swarm (your stacks, secrets, configs, networks), `config.yml` and `state/`

Not saved: the image registry (the installer fills it again; push your own images again)
and Docker volumes. Keep your own stacks' files in `/opt/ansibro/<stack name>/` so they are saved too:
their containers are paused while copied, like the apps above.

```bash
# on a server, after ssh
sudo ansibro-backup              # back up now
sudo ansibro-backup snapshots    # list the backups
```

To move the cluster to new servers, or after you lost it: make new servers, keep the same node names
and `ip` values (with `wireguard: true` only `host` changes), keep `state/`, and run:

```bash
# on your computer, in the ansibro folder
./install.sh -e restore=true
```

(`-e name=value` gives the installer an extra option.)

Each server gets its newest backup back, the swarm comes back with your stacks, and the databases are
loaded from their dumps. Old servers are removed from the swarm. A restore only runs on new servers.
If you lost `state/` too, get it back from the backup. You need the restic password (`state/secrets/restic`;
keep a copy of it outside the cluster). Install [restic](https://restic.net) on your computer, then run
this, with `<repository>` the `backup.repository` from `config.yml`:
`restic -r <repository> restore latest --host <first manager name> --include /opt/ansibro/backup/stage/installer --target .`

**Monitoring and alerts.** Add `prometheus` or `victoria` to `apps` (on a server with at least 2 GB
of free memory), and `monitoring:` with where alerts go: Telegram, email or a webhook (Slack and Discord
URLs are found by themselves). See [`config.example.yml`](../config.example.yml). Both choices do the same;
victoria uses less memory and disk.

On every server, agents collect the server (CPU, memory, disk, clock), its containers, the logs of
every container and of the system, and the stats of PostgreSQL, MariaDB, Redis and Valkey. Each minute,
every server also checks that its apps answer on their port, and writes the state of the swarm, the
last backup and WireGuard. Alerts are sent for:

- a server, an app, a container or a swarm service that is down, or restarts again and again
- a disk that is almost full (or fills up within a day), memory or CPU that stays high, a wrong clock
- a backup older than 26 hours, a WireGuard link that is down, a certificate that ends within 14 days
- a database or cache that is down or out of connections, web apps that answer with errors
- the monitoring itself: an agent or exporter that does not answer, alerts that cannot be sent

The rules are in [`roles/observability/files/alerts.yml`](../roles/observability/files/alerts.yml).
Grafana has an "Ansibro overview" dashboard. Logs: Grafana > Explore (prometheus), or
`https://logs.<domain>/select/vmui` (victoria).

**Who watches the monitoring?** If the monitoring server stops, it cannot send an alert. So there is a
test alert, `Watchdog`, that is always on. Something on another server checks that it is still there.
If it is gone, the monitoring is broken:

- Uptime Kuma (put `uptimekuma` on another server): add a monitor of type "HTTP(s) - Keyword",
  URL `http://<monitoring server ip>:9093/api/v2/alerts?filter=alertname=Watchdog`, keyword `Watchdog`.
  The install prints this URL. When the monitoring server, Alertmanager or the alert rules stop,
  the keyword is gone and Uptime Kuma tells you. The monitoring server sends an alert when Uptime Kuma's
  server is down, so the two watch each other.
- Or a heartbeat service outside the cluster, like [healthchecks.io](https://healthchecks.io): put its URL
  in `monitoring.heartbeat_url`. Alertmanager sends it a POST about every 2 minutes; set its period to 5 minutes.
  (Uptime Kuma's "Push" monitor does not work here: it takes only GET.)

**Remove an app.** Remove it from `config.yml` and run `./install.sh`. The installer stops it
(and its agents, Traefik page and timer). Its data stays in `/opt/ansibro/<app>` on its server:
`sudo rm -rf /opt/ansibro/<app>` if you do not need it. Not removed by itself: the app's database
(drop it in Postgres or MariaDB) and its old images in the registry.

**Remove a server.** Move its server apps to other servers first, then remove it from `config.yml`
and run `./install.sh -e remove_nodes=true`. The installer takes it out of the swarm (a manager is
demoted first) and the other servers' firewalls forget it. Without `-e remove_nodes=true` the
installer stops and lists the servers it would remove, so a typo cannot remove one.
Then turn the server off. Never remove the first manager.

**Add a server.** Add it to `config.yml`, after the first manager, and run `./install.sh`.

**Change a server's role** (worker to manager or back). The installer does not do this; it stops and
shows the command: `sudo docker node promote <name>` or `sudo docker node demote <name>` on a manager.

**Upgrade an app.** Change its tag (the version name) and digest (a fingerprint of that exact image)
in `versions.yml`, then run `./install.sh`.
Big Postgres upgrades (for example 18 to 19) need a dump (one file with all the data) and a restore by hand.
A new Docker version is installed one server at a time, so the swarm keeps running.

**Database replicas.** Give PostgreSQL a list of servers: `postgres: [db1, db2]`. The first is
the primary; apps use it. The others are replicas: read-only copies that follow it all the time
(alert `PostgresReplicaBehind` if one falls behind). If the primary dies, make a replica the new primary:

```bash
sudo docker exec -u postgres postgres pg_ctl promote -D /var/lib/postgresql/18/docker   # on the replica
```

Then put that server first in the list, take the old primary out of it (delete its
`/opt/ansibro/postgres` folder before you add it back, so it comes back as a replica), and run
`./install.sh` so the apps use the new primary. This is not automatic yet.

**Garage on 3 servers.** `garage: [s1, s2, s3]` keeps every file on all 3 servers, so one can
go down. Set it on the first install: the number of copies cannot change later.
