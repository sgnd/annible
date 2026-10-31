#!/usr/bin/env python3
"""Ansible inventory built from config.yml (path taken from $ANNIBLE_CONFIG).

It also checks config.yml, so mistakes stop the install early with a clear message.
"""

import ipaddress
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
GROUPS = {"manager": "managers", "worker": "workers", "standalone": "standalone"}
CONFIG_KEYS = {
    "domain", "acme_email", "acme_server", "acme_ca_cert", "tls", "tls_cert", "tls_key", "timezone", "arch",
    "ssh", "admin_allow_from", "nodes", "apps",
}
# Node names become hostnames, and must not clash with "swarm" or group names.
NODE_NAME = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
RESERVED_NAMES = {"swarm", "all", "managers", "workers", "standalone"}
SSH_KEYS = {"user", "key", "port", "allow_from"}
NODE_KEYS = {"name", "ip", "role", "labels"}


def fail(msg):
    sys.exit(f"config error: {msg}")


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_config():
    path = os.path.abspath(os.environ.get("ANNIBLE_CONFIG", "config.yml"))
    if not os.path.exists(path):
        fail(f"{path} not found (copy config.example.yml)")
    return load_yaml(path), os.path.dirname(path)


def load_bundle():
    """Return the bundle info (offline install), or {} when there is no bundle."""
    path = os.path.join(HERE, "bundle", "info.yml")
    return load_yaml(path) if os.path.exists(path) else {}


def check_ip_list(name, value):
    """A list of IPs or ranges, like [203.0.113.0/24, 198.51.100.7]. Empty is fine."""
    if value is None:
        return
    if not isinstance(value, list):
        fail(f"{name} must be a list, like [203.0.113.0/24]")
    for item in value:
        try:
            ipaddress.ip_network(str(item), strict=False)
        except ValueError:
            fail(f"{name}: {item} is not an IP or range")


def check_settings(cfg, bundle):
    unknown = set(cfg) - CONFIG_KEYS
    if unknown:
        fail(f"unknown setting {', '.join(sorted(unknown))} (typo?)")
    unknown = set(cfg.get("ssh") or {}) - SSH_KEYS
    if unknown:
        fail(f"unknown setting ssh.{', ssh.'.join(sorted(unknown))} (typo?)")
    if not cfg.get("domain"):
        fail("domain is required")
    tls = cfg.get("tls", "letsencrypt")
    if tls not in ("letsencrypt", "selfsigned", "custom"):
        fail("tls must be letsencrypt, selfsigned or custom")
    if tls == "letsencrypt" and not cfg.get("acme_email"):
        fail("acme_email is required for tls: letsencrypt")
    if tls == "custom" and not (cfg.get("tls_cert") and cfg.get("tls_key")):
        fail("tls: custom needs tls_cert and tls_key")
    if bundle and tls == "letsencrypt" and not cfg.get("acme_server"):
        fail("offline install: Let's Encrypt needs internet. Use tls: selfsigned or custom, "
             "or set acme_server to an ACME server in your network")
    if cfg.get("acme_ca_cert") and not cfg.get("acme_server"):
        fail("acme_ca_cert is only used with acme_server")
    if cfg.get("arch", "amd64") not in ("amd64", "arm64"):
        fail("arch must be amd64 or arm64")
    check_ip_list("ssh.allow_from", (cfg.get("ssh") or {}).get("allow_from"))
    check_ip_list("admin_allow_from", cfg.get("admin_allow_from"))
    if bundle and cfg.get("arch", "amd64") != bundle["arch"]:
        fail(f"the bundle is for {bundle['arch']}, but config.yml arch is {cfg.get('arch', 'amd64')}")


def build_nodes(nodes):
    if not nodes:
        fail("nodes is empty")

    groups = {g: [] for g in GROUPS.values()}
    hostvars = {}
    for node in nodes:
        name, ip, role = node.get("name"), node.get("ip"), node.get("role")
        unknown = set(node) - NODE_KEYS
        if unknown:
            fail(f"node {name}: unknown setting {', '.join(sorted(unknown))} (typo?)")
        if not name or not ip:
            fail(f"every node needs name and ip: {node}")
        if not NODE_NAME.match(str(name)) or name in RESERVED_NAMES:
            fail(f"node name {name}: use lowercase letters, numbers and -, not {', '.join(sorted(RESERVED_NAMES))}")
        if role not in GROUPS:
            fail(f"{name}: role must be one of {', '.join(GROUPS)}")
        if node.get("labels") and role == "standalone":
            fail(f"{name}: labels only work on swarm nodes (manager or worker)")
        if name in hostvars:
            fail(f"duplicate node name {name}")
        try:
            ipaddress.IPv4Address(ip)
        except ValueError:
            fail(f"{name}: ip must be an IPv4 address, got {ip}")
        if any(h["node_ip"] == ip for h in hostvars.values()):
            fail(f"duplicate ip {ip}")

        groups[GROUPS[role]].append(name)
        hostvars[name] = {
            "ansible_host": ip,
            "node_ip": ip,
            "node_role": role,
            "node_labels": {str(k): str(v) for k, v in (node.get("labels") or {}).items()},
            "node_apps": [],
        }

    if not groups["managers"]:
        fail("at least one manager is required")
    if len(groups["managers"]) % 2 == 0:
        fail("use an odd number of managers (1, 3 or 5)")
    return groups, hostvars


def build_apps(apps, catalog, hostvars):
    """Return {app: "swarm" or node name} in catalog order, after checking it."""
    apps = apps or {}
    for name, target in apps.items():
        if name not in catalog:
            fail(f"unknown app {name}, available: {', '.join(catalog)}")
        if not isinstance(target, str):
            fail(f"{name}: write it as '{name}: swarm' or '{name}: <node name>'")
        runs_on = catalog[name]["runs_on"]
        if target == "swarm" and runs_on != "swarm":
            fail(f"{name} runs on one server, set it to a node name")
        elif target != "swarm" and target not in hostvars:
            fail(f"{name}: must be swarm or a node name, got {target}")
        elif target != "swarm" and runs_on != "node":
            fail(f"{name} runs as a swarm service, set it to swarm")

    seen = {}
    for name in apps:
        category = catalog[name]["category"]
        if category in seen:
            fail(f"{seen[category]} and {name} are both {category}, pick one")
        seen[category] = name
    categories = {catalog[name]["category"] for name in apps}
    for name in apps:
        for dep in catalog[name].get("requires", []):
            if dep not in apps and dep not in categories:
                choices = [app for app, info in catalog.items() if info["category"] == dep]
                what = f"a {dep} ({' or '.join(choices)})" if choices else dep
                fail(f"{name} needs {what}, add it to apps")

    ordered = {name: apps[name] for name in catalog if name in apps}
    for name, target in ordered.items():
        if target != "swarm":
            hostvars[target]["node_apps"].append(name)
    return ordered


def build(cfg, base_dir):
    bundle = load_bundle()
    check_settings(cfg, bundle)
    groups, hostvars = build_nodes(cfg.get("nodes"))
    catalog = load_yaml(os.path.join(HERE, "catalog.yml"))
    apps = build_apps(cfg.get("apps"), catalog, hostvars)

    def from_config_dir(path):
        return os.path.join(base_dir, os.path.expanduser(path))

    ssh = cfg.get("ssh") or {}
    all_vars = {k: v for k, v in cfg.items() if k not in ("nodes", "apps")}
    for key in ("tls_cert", "tls_key", "acme_ca_cert"):
        if key in cfg:
            all_vars[key] = from_config_dir(cfg[key])
    all_vars.update(load_yaml(os.path.join(HERE, "versions.yml")))
    all_vars.update(
        offline=bool(bundle),
        bundle=bundle,
        apps=apps,
        catalog=catalog,
        swarm_apps=[name for name, target in apps.items() if target == "swarm"],
        ansible_user=ssh.get("user", "ubuntu"),
        ansible_port=ssh.get("port", 22),
        ansible_ssh_private_key_file=from_config_dir(ssh.get("key", "~/.ssh/id_ed25519")),
    )

    return {
        "_meta": {"hostvars": hostvars},
        "all": {"children": ["swarm", "standalone"], "vars": all_vars},
        "swarm": {"children": ["managers", "workers"]},
        "managers": {"hosts": groups["managers"]},
        "workers": {"hosts": groups["workers"]},
        "standalone": {"hosts": groups["standalone"]},
    }


def main():
    if "--host" in sys.argv:
        print("{}")
        return
    print(json.dumps(build(*load_config()), indent=2))


if __name__ == "__main__":
    main()
