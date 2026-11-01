# Advanced

Extra options: installer flags, GPU servers, Kong, Swarmpit, and the Authelia login for your own apps.
You do not need these for a normal install.

## More installer options

Extra `ansible-playbook` options go after the config file,
for example `./install.sh config.yml -v` (more output). Check mode (`--check`) is not supported.

## GPU servers

Set `gpu: true` on a server with an NVIDIA GPU. The installer installs the
NVIDIA driver that Ubuntu recommends (and restarts the server once), the NVIDIA Container Toolkit,
and makes `nvidia` Docker's default runtime there. Swarm servers get the label `gpu=true`. A service
that needs the GPU:

```yaml
    environment:
      NVIDIA_VISIBLE_DEVICES: all
    deploy:
      placement:
        constraints: [node.labels.gpu == true]
```

With monitoring, dcgm-exporter reports GPU use, temperature and memory (alerts `GpuTooHot`,
`GpuErrors`, `GpuMemoryFull`). GPU servers need internet. If the installer runs on a GPU server,
restart it by hand after the first run and run `./install.sh` again. The NVIDIA driver is not
open source; it is only installed with `gpu: true`.

## Kong

Kong runs on its own network, `kong`, shared only with Traefik. Put your API services on that
network too (`networks: [kong]`, external) so Kong can reach them. Other apps cannot reach Kong's admin API.

## Swarmpit

Swarmpit needs CouchDB 2.3 and InfluxDB 1.8, which are old. They are only on Swarmpit's own
network, but if you want only up-to-date software, choose Portainer.

## Authelia login in front of an app

Add `authelia@file` to the app's Traefik middlewares:
for a swarm app in `roles/<app>/templates/stack.yml.j2` (the `...middlewares` label, comma-separated),
for a server app with a web page set `traefik_route_middleware: authelia@file` in `roles/<app>/tasks/main.yml`.
A server app has one middleware, so this replaces its `admin_allow_from` limit.
