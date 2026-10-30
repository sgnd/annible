#!/usr/bin/env python3
"""Ansible inventory built from config.yml (path taken from $SWARM_CONFIG)."""

import ipaddress
import json
import os
import sys

import yaml

GROUPS = {"manager": "managers", "worker": "workers", "data": "data"}


def fail(msg):
    sys.exit(f"config error: {msg}")


def load_config():
    path = os.path.abspath(os.environ.get("SWARM_CONFIG", "config.yml"))
    try:
        with open(path) as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        fail(f"{path} not found (copy config.example.yml)")
    return cfg, os.path.dirname(path)


def build(cfg, base_dir):
    nodes = cfg.get("nodes") or []
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
        }

    if not groups["managers"]:
        fail("at least one manager is required")

    ssh = cfg.get("ssh") or {}
    key = os.path.expanduser(ssh.get("key", "~/.ssh/id_ed25519"))
    all_vars = {k: v for k, v in cfg.items() if k != "nodes"}
    all_vars.update(
        ansible_user=ssh.get("user", "ubuntu"),
        ansible_port=ssh.get("port", 22),
        ansible_ssh_private_key_file=os.path.join(base_dir, key),
    )

    return {
        "_meta": {"hostvars": hostvars},
        "all": {"children": ["swarm", "data"], "vars": all_vars},
        "swarm": {"children": ["managers", "workers"]},
        "managers": {"hosts": groups["managers"]},
        "workers": {"hosts": groups["workers"]},
        "data": {"hosts": groups["data"]},
    }


def main():
    if "--host" in sys.argv:
        print("{}")
        return
    print(json.dumps(build(*load_config()), indent=2))


if __name__ == "__main__":
    main()
