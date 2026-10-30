# Plan

Ansible installer untuk Docker Swarm. Online/offline, single/multi node, satu command.

## Topologi

- **Swarm (1+N)** — stateless: gateway, management, auth, app.
- **Data server (1)** — Docker Compose: database, cache, storage, queue, monitoring.

## Katalog

| Kategori   | Default    | Opsi      |
|------------|------------|-----------|
| gateway    | traefik    | kong      |
| management | portainer  | swarmpit  |
| database   | postgres   | mariadb   |
| cache      | redis      | valkey    |
| storage    | rustfs     | garage    |
| queue      | rabbitmq   | nats      |
| auth       | keycloak   | authelia  |
| monitoring | uptimekuma | beszel    |

Isi `none` untuk skip. Registry lokal selalu dipasang (dibutuhkan untuk offline).

## Pemakaian

```bash
cp config.example.yml config.yml   # isi IP, ssh key, role node, pilihan app
./build-bundle.sh                  # di mesin online → bundle.tar.gz
./install.sh                       # di manager-1
```

## Struktur

```
config.example.yml   versions.yml   build-bundle.sh   install.sh
inventory.py         site.yml
roles/
  common  docker  swarm  registry
  traefik  kong  portainer  swarmpit
  postgres  mariadb  redis  valkey  rustfs  garage
  rabbitmq  nats  keycloak  authelia  uptimekuma  beszel
README.md  LICENSE
```

## Aturan

- Versi dikunci di `versions.yml` (tag + digest). Tidak ada `latest`.
- Password digenerate otomatis, disimpan di `state/` (Ansible Vault).
- Port data server hanya dibuka untuk IP node Swarm.
- TLS: Let's Encrypt, fallback self-signed.
- Bisa dijalankan ulang (idempotent) — sekaligus untuk tambah node.

## Urutan kerja

1. common, docker, swarm, registry — online
2. bundle offline
3. traefik/kong, portainer/swarmpit
4. data server: postgres/mariadb, redis/valkey, rustfs/garage, rabbitmq/nats
5. keycloak/authelia, uptimekuma/beszel

Tiap tahap dites di VM (1 node & multi node) sebelum lanjut.
