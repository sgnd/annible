# Offline install

For servers with no internet (for example only VPN access).

**1. Get a bundle.** Each release on GitHub has them, for both CPU types and Ubuntu versions.
They come in parts (GitHub allows 2 GB per file); put the parts back together and check them:

```bash
cat ansibro-24.04-amd64.tar.gz.part* > ansibro-24.04-amd64.tar.gz
sha256sum -c ansibro-24.04-amd64.tar.gz.sha256   # on a Mac: shasum -a 256 -c ...
```

Or build one yourself: **on a machine with internet and Docker**, build a bundle for the CPU and Ubuntu version
of your servers. A Mac (Docker Desktop or OrbStack) can build both CPU types. On Linux,
building for the other CPU type needs QEMU, which lets one CPU type run programs for the other.
This command installs it: `docker run --privileged --rm tonistiigi/binfmt --install all`.

```bash
./build-bundle.sh amd64          # Intel/AMD servers, Ubuntu 24.04
./build-bundle.sh arm64 26.04    # ARM servers, Ubuntu 26.04
```

This makes `dist/ansibro-<ubuntu>-<arch>.tar.gz` (about 2.5 GB). It holds this project, apt packages,
Ansible and all Docker images from `versions.yml`. Your project folder is not changed.

**2. Copy it to the first manager**, together with your SSH private key and, if you use them,
your `tls_cert`/`tls_key`/`acme_ca_cert` files (the bundle leaves out keys and certificates).
The installer connects over SSH to every server, the first manager itself too, so that key must
be allowed on all servers. Then run the installer there:

```bash
tar -xzf ansibro-24.04-amd64.tar.gz
cd ansibro
cp config.example.yml config.yml   # set tls: selfsigned (or custom), and ssh.key
./install.sh
```

The installer sees the `bundle/` folder and uses it instead of the internet.
The servers' own apt settings are not changed.

Notes:
- Every server must run the bundle's Ubuntu version and CPU type.
- Let's Encrypt needs internet. Use `tls: selfsigned`, `tls: custom`, or an ACME server
  in your network (`acme_server`, see `config.example.yml`).
- Time sync (chrony) needs a time server. Without internet, use one in your network: on each server
  put `server <time server ip> iburst` in `/etc/chrony/sources.d/local.sources`, then run
  `sudo chronyc reload sources`.
