# Getting started

This guide is for your first install. It starts from zero: no server, no cluster.
At the end you have one server with a web gateway (Traefik), a page to manage your
apps (Portainer) and a database (PostgreSQL), all with HTTPS and passwords.

You need to know how to open a terminal and type commands. That is all.
A word you do not know? See [Words](#words) at the end.

You need:

- A computer with macOS or Linux, with `git` and Python 3.12 or newer. This is where you run the installer.
  Check with `python3 --version`. Too old or missing? On a Mac: `brew install python@3.12 git`
  (no `brew`? Get it from [brew.sh](https://brew.sh)). On Ubuntu: `sudo apt install git python3 python3-venv`.
- A domain name you own, for example `example.com`, where you can add DNS records.
- A little money for a cloud server (a few dollars a month).

## 1. Make an SSH key

An SSH key lets the installer log in to your server without a password.
If you already have `~/.ssh/id_ed25519`, skip this step.

```bash
ssh-keygen -t ed25519
```

Press Enter for every question. This makes two files:
`~/.ssh/id_ed25519` (private, never share it) and `~/.ssh/id_ed25519.pub` (public).

## 2. Rent a server

Make a server at any cloud provider (DigitalOcean, Hetzner, AWS, ...) with:

- **Ubuntu 24.04** (or 26.04)
- at least **2 CPUs and 4 GB of memory**
- your **public SSH key**: paste the text of `~/.ssh/id_ed25519.pub` when the provider asks for it
- if your provider has a cloud firewall (on AWS: a "security group"), open ports **22** (SSH),
  **80** and **443** (web pages) to everyone

Write down the server's **public IP address**, for example `203.0.113.10`.
Check that you can log in (the user is often `root` or `ubuntu`, your provider tells you):

```bash
ssh root@203.0.113.10
```

The first time it asks `Are you sure you want to continue connecting (yes/no)?`. Type `yes`.
Type `exit` to leave the server again.

The installer needs a user that can use `sudo` without a password. `root` always can.
On most clouds the `ubuntu` user can too.

Also write down the server's **private IP**, if your provider shows one (often it starts with `10.`).
It is how servers talk to each other inside the provider's network.

## 3. Point your domain to the server

At the company where you bought your domain, add one DNS record:

| Type | Name | Value |
|------|------|-------|
| A | `*` | your server's public IP |

The `*` means "every name", so `traefik.example.com`, `portainer.example.com` and so on all go to your server.
It can take a few minutes, sometimes an hour. Check it:

```bash
ping -c 1 portainer.example.com    # must show your server's IP
```

`Unknown host` or another IP? Wait a few minutes and try again. If it still does not work after an hour,
check the record at your domain company: the name must be `*` and the value your server's public IP.

## 4. Download Ansibro and write config.yml

On your computer:

```bash
git clone https://github.com/sgnd/ansibro.git
cd ansibro
cp config.example.yml config.yml
```

Open `config.yml` in a text editor. It is long, but every line is explained, and most
can stay as they are. Change `domain`, `acme_email` and `ssh` as below.
Then **replace the whole `nodes:` part and the whole `apps:` part** with the ones below.
(The example has more servers and apps. If you keep an app on a server that you removed, the installer stops with an error.)

```yaml
domain: example.com             # your domain
acme_email: you@example.com     # Let's Encrypt sends notices about your certificates here

ssh:
  user: root                    # the user from step 2
  key: ~/.ssh/id_ed25519        # the private key from step 1

nodes:
  - name: server1
    ip: 10.0.0.5                # the private IP from step 2. No private IP? Write the public IP here too.
    host: 203.0.113.10          # the public IP: where the installer connects
    role: manager

apps:
  traefik: swarm
  portainer: swarm
  postgres: server1
```

You can add more apps later. The [Apps table](../README.md#apps) lists them all.

## 5. Run the installer

```bash
./install.sh
```

It checks `config.yml` first. If something is wrong, it tells you what to fix.
Then it sets up the server. This takes a while. Lines that say `ok` or `changed` are good;
red lines that say `FAILED` are not (see [Troubleshooting](../README.md#troubleshooting)).

At the end it prints the address of each app. It also saves them, with all passwords, in `state/summary.md`.

Want to be sure everything works? Run the checks in [Check that everything works](../README.md#check-that-everything-works).

## 6. Open your apps

Open `https://portainer.example.com` in your browser. Portainer shows your containers and lets you
start your own apps. The passwords are in `state/summary.md`. (If you set up encryption for `state/`,
run `scripts/state.sh open` first, and `scripts/state.sh close` when you are done.)

You are done. Next:

- **Keep the `state/` folder safe.** It holds every password. Without it, the next run makes new
  passwords that do not match your database. Copy it somewhere safe, or keep it encrypted:
  install [age](https://age-encryption.org) (`brew install age`, or `sudo apt install age`), then run
  `mkdir -p ~/.config/ansibro && age-keygen -o ~/.config/ansibro/age.key` once, and keep a copy of that key file
  (for example in a password manager). From the next run, `state/` is kept encrypted.
- **Run `./install.sh` again** whenever you change `config.yml`, for example to add an app or a server.
  It only changes what is different.
- **Add backups and alerts**: see "Back up and restore" and "Monitoring and alerts" in [How to](../README.md#how-to).

## Words

| Word | What it means |
|------|---------------|
| **server**, **node** | A computer that runs all the time, usually rented from a cloud provider. Ansibro calls each server in `config.yml` a node. |
| **cluster** | A group of servers that work together, so an app can run on any of them. |
| **Docker** | A tool to run apps in **containers**. |
| **container** | An app packed with everything it needs, running apart from other apps on the same server. |
| **image** | The package a container is started from, like `postgres:18`. |
| **Docker Swarm** | Docker's own way to join servers into a cluster. Ansibro uses it by default. |
| **k3s**, **Kubernetes** | Kubernetes is another, bigger way to run a cluster. k3s is a small Kubernetes. You can pick it instead of Swarm. |
| **manager** | A server that controls the cluster and runs swarm apps. Use 1, 3 or 5. |
| **worker** | A server in the cluster that only runs swarm apps. |
| **standalone** | A server that is not in the cluster. It runs server apps, like a database. |
| **first manager** | The first server with `role: manager` in `config.yml`. Some apps keep their data there. |
| **stack** | A group of containers that belong together and are started as one, in a swarm. |
| **registry** | A place that stores images. Ansibro runs its own on your managers, so servers do not download from the internet each time. |
| **label** | A tag on a server, like `tier=app`, that tells the swarm which apps may run there. |
| **swarm app** | An app that the cluster runs, on any manager or worker (for example Traefik, Portainer). |
| **server app** | An app that runs on the one server you name (for example PostgreSQL). Its data stays on that server. |
| **SSH** | The way to log in to a server and type commands there, over the network. |
| **SSH key** | A pair of files that logs you in to a server without a password. The public one goes on the server. |
| **sudo** | Run a command as the admin (root) user. "Passwordless sudo" means it does not ask for a password. |
| **IP address** | The number of a computer on a network, like `203.0.113.10`. A **public IP** can be reached from the internet; a **private IP** only inside your provider's network. |
| **domain**, **DNS** | A domain is a name like `example.com`. DNS is the system that turns names into IP addresses. |
| **DNS record**, **A record** | One line in your domain's DNS settings. An A record says: this name goes to this IP address. |
| **wildcard DNS** | A DNS record for `*.example.com`: every name under your domain goes to the same IP. |
| **HTTPS**, **TLS**, **certificate** | HTTPS is the encrypted version of web pages. It needs a certificate for your domain. |
| **Let's Encrypt** | A free service that gives certificates. Ansibro asks it for you. |
| **ACME** | The way Let's Encrypt (and some other services) give out certificates. |
| **Traefik** | The gateway: it receives all web traffic and sends it to the right app, with HTTPS. |
| **firewall** | Rules about which network ports are open. Ansibro opens only what is needed and blocks the rest. |
| **port** | A number that tells which app on a server a connection is for. Web pages use 80 (HTTP) and 443 (HTTPS). |
| **WireGuard** | An encrypted network between your servers. Turn it on when servers talk over the internet. |
| **amd64**, **arm64** | The two kinds of CPU. Intel and AMD are amd64. ARM servers (like AWS Graviton) are arm64. |
| **offline bundle** | One big file with everything Ansibro needs, for servers that have no internet. |
| **`state/` folder** | The folder where Ansibro keeps the passwords it made. Back it up. |
| **Portainer** | A web page to see and manage your containers. |
| **PostgreSQL** | A popular database. |
| **tag**, **digest** | The version name of an image (`18.1`), and a fingerprint of that exact image, so it can not change. |
| **dump** | One file with all the data of a database, used for backups and big upgrades. |
| **Docker Compose** | A way to start containers from a file. Ansibro uses it for server apps. |
| **YAML** | The format of `config.yml`: `name: value` lines, with spaces at the start to show what belongs together. Use spaces, not tabs. |
| **VPC** | A private network for your servers at a cloud provider. |
| **Ansible**, **playbook** | Ansible is the tool Ansibro uses to set up the servers. A playbook is its list of steps. You do not need to learn it. |
