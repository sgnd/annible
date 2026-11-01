# Examples of config.yml

Small examples for common setups. [`config.example.yml`](../config.example.yml) explains every setting.

**One server.** Everything on one machine. `ip` is the private IP, `host` the public IP where the
installer connects (no private IP? Use the public IP for both):

```yaml
nodes:
  - { name: server1, ip: 10.0.0.10, host: 203.0.113.10, role: manager }
apps:
  traefik: swarm
  portainer: swarm
  postgres: server1
  redis: server1
```

**Swarm plus a data server:**

```yaml
nodes:
  - { name: app1,  ip: 10.0.0.11, role: manager }
  - { name: app2,  ip: 10.0.0.12, role: worker }
  - { name: data1, ip: 10.0.0.21, role: standalone }
apps:
  traefik: swarm
  portainer: swarm
  postgres: data1
  rustfs: data1
```

**Servers with more than one IP** (for example AWS: a public IP for SSH, a private IP inside the VPC).
`ip` is what the swarm uses, `host` is where the installer connects:

```yaml
nodes:
  - { name: app1, ip: 10.0.0.11, host: 203.0.113.11, role: manager }
  - { name: app2, ip: 10.0.0.12, host: 203.0.113.12, role: worker }
```

**Encrypted network between servers** (WireGuard). For servers that talk over the internet,
in different clouds, or that may move. `host` is the server's real address, `ip` is a new
address on the WireGuard network that you pick, and it never has to change:

```yaml
wireguard: true
nodes:
  - { name: app1,  ip: 10.99.0.11, host: 203.0.113.11, role: manager }
  - { name: app2,  ip: 10.99.0.12, host: 198.51.100.7, role: worker }
  - { name: data1, ip: 10.99.0.21, host: 192.0.2.30,   role: standalone }
```

Each `host` must be reachable from the other servers (WireGuard) and from the installer (SSH).
Open UDP port 51820 between the servers' `host` addresses in your cloud firewall (security group).
Turn it on for a new cluster: an existing swarm cannot change its servers' addresses.

See [`config.example.yml`](../config.example.yml) for every setting.
