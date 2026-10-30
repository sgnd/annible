#!/usr/bin/env python3
"""Ansible inventory built from config.yml (path taken from $SWARM_CONFIG)."""

import ipaddress
import json
import os
import sys

import yaml

GROUPS = {"manager": "managers", "worker": "workers", "standalone": "standalone"}
CATALOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog.yml")


def fail(msg):
    sys.exit(f"config error: {msg}")


def load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_config():
    path = os.path.abspath(os.environ.get("SWARM_CONFIG", "config.yml"))
    if not os.path.exists(path):
        fail(f"{path} not found (copy config.example.yml)")
    return load_yaml(path), os.path.dirname(path)


def build_nodes(nodes):
    if not nodes:
        fail("nodes is empty")

    groups = {g: [] for g in GROUPS.values()}
    hostvars = {}
    for node in nodes:
        name, ip, role = node.get("name"), node.get("ip"), node.get("role")
        if not name or not ip:
            fail(f"every node needs name and ip: {node}")
        if role not in GROUPS:
            fail(f"{name}: role must be one of {', '.join(GROUPS)}")
        if name in hostvars:
            fail(f"duplicate node name {name}")
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            fail(f"{name}: invalid ip {ip}")
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
    return groups, hostvars


def build_apps(apps, catalog, hostvars):
    """Normalize apps to {name: {"on": ...}} in catalog order and validate them."""
    normalized = {}
    for name, spec in (apps or {}).items():
        if name not in catalog:
            fail(f"unknown app {name}, available: {', '.join(catalog)}")
        if spec is None:
            spec = {}
        elif not isinstance(spec, dict):
            spec = {"on": spec}
        spec.setdefault("on", "swarm")

        target = spec["on"]
        runs_on = catalog[name]["runs_on"]
        if target == "swarm":
            if runs_on != "swarm":
                fail(f"{name} must run on a node, set it to a node name")
        elif target in hostvars:
            if runs_on != "node":
                fail(f"{name} runs as a swarm service, set it to swarm")
            hostvars[target]["node_apps"].append(name)
        else:
            fail(f"{name}: on must be swarm or a node name, got {target}")
        normalized[name] = spec

    seen = {}
    for name in normalized:
        category = catalog[name]["category"]
        if category in seen:
            fail(f"{seen[category]} and {name} are both {category}, pick one")
        seen[category] = name
        for dep in catalog[name].get("requires", []):
            if dep not in normalized:
                fail(f"{name} requires {dep}")

    return {name: normalized[name] for name in catalog if name in normalized}


def build(cfg, base_dir):
    groups, hostvars = build_nodes(cfg.get("nodes"))
    apps = build_apps(cfg.get("apps"), load_yaml(CATALOG), hostvars)

    ssh = cfg.get("ssh") or {}
    key = os.path.expanduser(ssh.get("key", "~/.ssh/id_ed25519"))
    all_vars = {k: v for k, v in cfg.items() if k not in ("nodes", "apps")}
    all_vars.update(
        apps=apps,
        swarm_apps=[name for name, spec in apps.items() if spec["on"] == "swarm"],
        ansible_user=ssh.get("user", "ubuntu"),
        ansible_port=ssh.get("port", 22),
        ansible_ssh_private_key_file=os.path.join(base_dir, key),
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
