# Third-party software

This project is MIT licensed. The repository has no other software in it, but the installer
downloads and runs the software below. Each one keeps its own license.

The offline bundle (`build-bundle.sh`) contains copies of this software: Docker images,
Ubuntu and Docker apt packages, and Python packages. If you share a bundle, you share them too.
Their source code is at the links below and at https://launchpad.net/ubuntu (apt packages).

| Software | License | Source |
|----------|---------|--------|
| Docker Engine | Apache-2.0 | https://github.com/moby/moby |
| containerd | Apache-2.0 | https://github.com/containerd/containerd |
| Docker Buildx and Compose plugins | Apache-2.0 | https://github.com/docker/buildx, https://github.com/docker/compose |
| Ansible (ansible-core) | GPL-3.0 | https://github.com/ansible/ansible |
| Python packages for Ansible (bcrypt, cffi, cryptography, Jinja2, MarkupSafe, packaging, pycparser, PyYAML, resolvelib) | MIT, BSD, Apache-2.0 | https://pypi.org (versions in `requirements.txt`) |
| Ansible collections: ansible.posix, community.general, community.library_inventory_filtering_v1 | GPL-3.0 | https://github.com/ansible-collections |
| Docker Registry (distribution) | Apache-2.0 | https://github.com/distribution/distribution |
| Traefik | MIT | https://github.com/traefik/traefik |
| Portainer CE | zlib | https://github.com/portainer/portainer |
| Kong Gateway (OSS) | Apache-2.0 | https://github.com/Kong/kong |
| Swarmpit | EPL-1.0 | https://github.com/swarmpit/swarmpit |
| CouchDB (for Swarmpit) | Apache-2.0 | https://github.com/apache/couchdb |
| InfluxDB 1.x (for Swarmpit) | MIT | https://github.com/influxdata/influxdb |
| Keycloak | Apache-2.0 | https://github.com/keycloak/keycloak |
| Authelia | Apache-2.0 | https://github.com/authelia/authelia |
| Uptime Kuma | MIT | https://github.com/louislam/uptime-kuma |
| Beszel | MIT | https://github.com/henrygd/beszel |
| PostgreSQL | PostgreSQL | https://www.postgresql.org |
| MariaDB | GPL-2.0 | https://github.com/MariaDB/server |
| Redis 8 | AGPL-3.0 (one of its three licenses) | https://github.com/redis/redis |
| Valkey | BSD-3-Clause | https://github.com/valkey-io/valkey |
| RustFS | Apache-2.0 | https://github.com/rustfs/rustfs |
| Garage | AGPL-3.0 | https://git.deuxfleurs.fr/Deuxfleurs/garage |
| RabbitMQ | MPL-2.0 | https://github.com/rabbitmq/rabbitmq-server |
| NATS | Apache-2.0 | https://github.com/nats-io/nats-server |
| Prometheus, Alertmanager, node-exporter, mysqld-exporter, postgres-exporter | Apache-2.0 | https://github.com/prometheus |
| Loki | AGPL-3.0 | https://github.com/grafana/loki |
| Grafana | AGPL-3.0 | https://github.com/grafana/grafana |
| VictoriaMetrics, VictoriaLogs, vmalert | Apache-2.0 | https://github.com/VictoriaMetrics/VictoriaMetrics, https://github.com/VictoriaMetrics/VictoriaLogs |
| cAdvisor | Apache-2.0 | https://github.com/google/cadvisor |
| Vector | MPL-2.0 | https://github.com/vectordotdev/vector |
| redis_exporter | MIT | https://github.com/oliver006/redis_exporter |

Versions are in [`versions.yml`](versions.yml). We use the official images without changes.
