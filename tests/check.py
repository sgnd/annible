#!/usr/bin/env python3
"""End-to-end check: test every installed app for real.

Run it after ./install.sh, on the same machine and in the same folder:

    .venv/bin/python tests/check.py [config.yml]

It reads config.yml, logs in to each app with the passwords in state/secrets/,
and prints PASS or FAIL per check. Exit code 0 = everything passed.
The checks run on the first manager: here if this is the first manager,
otherwise over SSH with the same settings as the installer.
Passwords are sent through stdin, so they never show up in a process list.
"""

import datetime
import hashlib
import hmac
import json
import os
import shlex
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
if len(sys.argv) > 1:
    os.environ["ANNIBLE_CONFIG"] = sys.argv[1]
os.environ.setdefault("ANNIBLE_CONFIG", "config.yml")
import inventory  # noqa: E402

inv = inventory.build(*inventory.load_config())
CFG = inv["all"]["vars"]
HOSTS = inv["_meta"]["hostvars"]
APPS = CFG["apps"]
DOMAIN = CFG["domain"]
LEADER = inv["managers"]["hosts"][0]
LEADER_IP = HOSTS[LEADER]["node_ip"]
REGISTRY = f"{LEADER_IP}:{CFG['registry_port']}"
IMAGES = CFG["images"]
WEB = "traefik" in APPS  # web pages only exist with traefik
ON_LEADER = socket.gethostname() == LEADER  # the installer sets each server's hostname to its name
results = []


# ---------- helpers ----------

def secret(name):
    with open(os.path.join(HERE, "state", "secrets", name)) as f:
        return f.read().strip()


def ip_of(app):
    return HOSTS[APPS[app]]["node_ip"]


def on_leader(cmd, stdin=None):
    """Run a command on the first manager. Returns (exit code, output)."""
    if not ON_LEADER:
        cmd = ["ssh", "-i", CFG["ansible_ssh_private_key_file"], "-p", str(CFG["ansible_port"]),
               "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
               f"{CFG['ansible_user']}@{LEADER_IP}", shlex.join(cmd)]
    p = subprocess.run(cmd, input=stdin, capture_output=True, text=True, timeout=180)
    return p.returncode, (p.stdout + p.stderr).strip()


def curl(url, user=None, data=None, headers=(), resolve=None):
    """HTTP request from the first manager. Returns (status, body). Secrets go in through stdin."""
    config = [f'url = "{url}"', 'silent', 'insecure', 'max-time = 20', 'write-out = "\\n%{http_code}"']
    if resolve:
        config.append(f'resolve = "{resolve}"')
    if user:
        config.append(f'user = "{user}"')
    if data is not None:
        config.append(f"data = {json.dumps(data)}")
    config += [f'header = "{h}"' for h in headers]
    _, out = on_leader(["curl", "--config", "-"], stdin="\n".join(config) + "\n")
    body, _, code = out.rpartition("\n")
    return code, body


def https(sub, path="/", **kwargs):
    """Request https://<sub>.<domain><path> through Traefik.

    Traefik looks for new apps every 5 seconds, so right after an install a page can
    answer 404 or 502 for a moment. Try again a few times before reporting it.
    """
    host = f"{sub}.{DOMAIN}"
    for _ in range(4):
        code, body = curl(f"https://{host}{path}", resolve=f"{host}:443:{LEADER_IP}", **kwargs)
        if code not in ("404", "502", "503") or (sub == "kong" and "no Route matched" in body):
            break
        time.sleep(3)
    return code, body


def client(image, *args, env=()):
    """Run a tool from an app image (for example psql) on the first manager. env goes in through stdin."""
    cmd = ["sudo", "docker", "run", "--rm", "--network", "host", "--env-file", "/dev/stdin",
           f"{REGISTRY}/{image}:{IMAGES[image]['tag']}", *args]
    return on_leader(cmd, stdin="\n".join(env) + "\n")


def python_on_leader(code, data):
    """Run a small Python program on the first manager; data goes in as JSON on stdin."""
    return on_leader(["python3", "-c", code], stdin=json.dumps(data))


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if not ok and detail else ""))


def s3_list_buckets(endpoint, access_key, secret_key, region):
    """Call S3 ListBuckets with AWS signature v4. Returns the HTTP status."""
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    host = endpoint.split("//")[1]
    payload = hashlib.sha256(b"").hexdigest()
    canonical = f"GET\n/\n\nhost:{host}\nx-amz-content-sha256:{payload}\nx-amz-date:{amz_date}\n\nhost;x-amz-content-sha256;x-amz-date\n{payload}"
    scope = f"{day}/{region}/s3/aws4_request"
    to_sign = f"AWS4-HMAC-SHA256\n{amz_date}\n{scope}\n{hashlib.sha256(canonical.encode()).hexdigest()}"
    key = ("AWS4" + secret_key).encode()
    for part in (day, region, "s3", "aws4_request"):
        key = hmac.new(key, part.encode(), hashlib.sha256).digest()
    signature = hmac.new(key, to_sign.encode(), hashlib.sha256).hexdigest()
    auth = f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature={signature}"
    code, _ = curl(endpoint + "/", headers=[f"Authorization: {auth}", f"x-amz-date: {amz_date}", f"x-amz-content-sha256: {payload}"])
    return code


TCP_OPEN = """
import json, socket, sys
d = json.load(sys.stdin)
socket.create_connection((d["ip"], d["port"]), timeout=5).close()
"""

NATS_LOGIN = """
import json, socket, sys
d = json.load(sys.stdin)
s = socket.create_connection((d["ip"], 4222), timeout=5)
s.recv(4096)  # INFO line
s.sendall(("CONNECT " + json.dumps({"user": "admin", "pass": d["password"], "verbose": False}) + "\\r\\nPING\\r\\n").encode())
print(s.recv(4096).decode().strip())
"""


# ---------- checks ----------

def check_swarm():
    _, out = on_leader(["sudo", "docker", "service", "ls", "--format", "{{.Name}} {{.Replicas}}"])
    for line in out.splitlines():
        name, replicas = line.split()[:2]
        running, wanted = replicas.split("/")
        check(f"swarm service {name} running ({replicas})", running == wanted)
    _, out = on_leader(["sudo", "docker", "node", "ls", "--format", "{{.Hostname}} {{.Status}}"])
    for node in inv["managers"]["hosts"] + inv["workers"]["hosts"]:
        check(f"swarm node {node} ready", f"{node} Ready" in out)
    # A swarm made before v1.0.1 keeps Docker's old range (shown as []), so only check newer ones.
    _, pool = on_leader(["sudo", "docker", "info", "--format", "{{.Swarm.Cluster.DefaultAddrPool}}"])
    if pool == "[]":
        print("SKIP  swarm networks use the 10.200.0.0/16 range  (swarm made before v1.0.1)")
    else:
        _, out = on_leader(["sudo", "docker", "network", "inspect", "public", "--format", "{{range .IPAM.Config}}{{.Subnet}}{{end}}"])
        check("swarm networks use the 10.200.0.0/16 range", out.startswith("10.200."), out)
    code, _ = curl(f"https://{REGISTRY}/v2/")
    check("registry refuses access without login", code == "401", code)


def check_traefik():
    code, _ = curl(f"http://traefik.{DOMAIN}/", resolve=f"traefik.{DOMAIN}:80:{LEADER_IP}")
    check("traefik redirects HTTP to HTTPS", code in ("301", "308"), code)
    check("traefik dashboard needs a password", https("traefik", "/dashboard/")[0] == "401")
    check("traefik dashboard opens with the password", https("traefik", "/dashboard/", user="admin:" + secret("traefik_admin"))[0] == "200")


def check_portainer():
    code, body = https("portainer", "/api/auth", data=json.dumps({"username": "admin", "password": secret("portainer_admin")}))
    check("portainer admin login", code == "200" and "jwt" in body, code)


def check_swarmpit():
    check("swarmpit needs the Traefik password", https("swarmpit")[0] == "401")
    check("swarmpit page opens with the password", https("swarmpit", user="admin:" + secret("traefik_admin"))[0] == "200")


def check_kong():
    code, body = https("kong")
    check("kong proxy answers", code == "404" and "no Route matched" in body, code)
    check("kong manager needs a password", https("kong-manager")[0] == "401")
    pw = "admin:" + secret("traefik_admin")
    check("kong manager opens with the password", https("kong-manager", user=pw)[0] == "200")
    code, body = https("kong-manager", "/api/", user=pw)
    check("kong admin API works", code == "200" and "version" in body, code)
    # From the public network (where other apps are), the admin API must not be reachable.
    _, out = on_leader(["sudo", "docker", "run", "--rm", "--network", "public", f"{REGISTRY}/kong:{IMAGES['kong']['tag']}",
                        "curl", "-s", "-m", "5", "-o", "/dev/null", "-w", "%{http_code}", "http://kong_kong:8001/"])
    check("kong admin API is not reachable from other apps", not out.endswith("200"), out[-80:])


def check_keycloak():
    form = f"grant_type=password&client_id=admin-cli&username=admin&password={secret('keycloak_admin')}"
    code, body = https("keycloak", "/realms/master/protocol/openid-connect/token", data=form)
    check("keycloak admin login", code == "200" and "access_token" in body, code)


def check_authelia():
    hdr = ["Content-Type: application/json"]
    code, body = https("authelia", "/api/firstfactor", data=json.dumps({"username": "admin", "password": secret("authelia_admin")}), headers=hdr)
    check("authelia login with the right password", '"OK"' in body, code)
    _, body = https("authelia", "/api/firstfactor", data=json.dumps({"username": "admin", "password": "wrong"}), headers=hdr)
    check("authelia refuses a wrong password", '"KO"' in body)


def check_postgres():
    _, out = client("postgres", "psql", "-h", ip_of("postgres"), "-U", "postgres", "-tAc", "select 1", env=[f"PGPASSWORD={secret('postgres')}"])
    check("postgres login", out.strip() == "1", out[-200:])
    for app in ("kong", "keycloak", "authelia"):
        if app in APPS:
            _, out = client("postgres", "psql", "-h", ip_of("postgres"), "-U", app, "-tAc", "select 1",
                            env=[f"PGPASSWORD={secret(app + '_db')}"])
            check(f"postgres database for {app}", out.strip() == "1", out[-200:])


def check_mariadb():
    _, out = client("mariadb", "mariadb", "-h", ip_of("mariadb"), "-uroot", "-N", "-e", "select 1", env=[f"MYSQL_PWD={secret('mariadb')}"])
    check("mariadb login", out.strip() == "1", out[-200:])
    for app in ("keycloak", "authelia"):
        if app in APPS:
            _, out = client("mariadb", "mariadb", "-h", ip_of("mariadb"), f"-u{app}", "-N", "-e", "select 1",
                            env=[f"MYSQL_PWD={secret(app + '_db')}"])
            check(f"mariadb database for {app}", out.strip() == "1", out[-200:])


def check_cache(app):
    cli = "redis-cli" if app == "redis" else "valkey-cli"
    _, out = client(app, cli, "-h", ip_of(app), "ping", env=[f"REDISCLI_AUTH={secret(app)}"])
    check(f"{app} login", "PONG" in out, out[-200:])
    _, out = client(app, cli, "-h", ip_of(app), "ping", env=["REDISCLI_AUTH=wrong"])
    check(f"{app} refuses a wrong password", "PONG" not in out)


def check_rustfs():
    status = s3_list_buckets(f"http://{ip_of('rustfs')}:9000", secret("rustfs_access_key"), secret("rustfs_secret_key"), "us-east-1")
    check("rustfs S3 login with the keys", status == "200", status)
    if WEB:
        check("rustfs console", https("rustfs", "/rustfs/console/index.html")[0] == "200")


def check_garage():
    status = s3_list_buckets(f"http://{ip_of('garage')}:3900", "GK" + secret("garage_access_key"), secret("garage_secret_key"), "garage")
    check("garage S3 login with the keys", status == "200", status)


def check_rabbitmq():
    code, out = python_on_leader(TCP_OPEN, {"ip": ip_of("rabbitmq"), "port": 5672})
    check("rabbitmq AMQP port open", code == 0, out[-200:])
    if WEB:
        code, body = https("rabbitmq", "/api/overview", user="admin:" + secret("rabbitmq"))
        check("rabbitmq UI login", code == "200" and "rabbitmq_version" in body, code)


def check_nats():
    _, out = python_on_leader(NATS_LOGIN, {"ip": ip_of("nats"), "password": secret("nats")})
    check("nats login", out.startswith("PONG"), out[-200:])
    if WEB:
        check("nats monitoring needs a password", https("nats", "/varz")[0] == "401")
        check("nats monitoring opens with the password", https("nats", "/varz", user="admin:" + secret("traefik_admin"))[0] == "200")


def check_uptimekuma():
    check("uptime kuma needs the Traefik password", https("uptimekuma")[0] == "401")
    check("uptime kuma page opens with the password", https("uptimekuma", user="admin:" + secret("traefik_admin"))[0] in ("200", "302"))


def check_beszel():
    url = f"http://{ip_of('beszel')}:8090"
    code, body = curl(url + "/api/collections/users/auth-with-password",
                      data=json.dumps({"identity": f"admin@{DOMAIN}", "password": secret("beszel_admin")}),
                      headers=["Content-Type: application/json"])
    check("beszel admin login", code == "200", code)
    if code != "200":
        return
    token = json.loads(body)["token"]
    _, body = curl(url + "/api/collections/systems/records?perPage=500", headers=[f"Authorization: {token}"])
    systems = {s["name"]: s["status"] for s in json.loads(body)["items"]}
    for host in HOSTS:
        check(f"beszel sees {host} up", systems.get(host) == "up", systems.get(host, "missing"))
    check("beszel page", https("beszel")[0] == "200")


CHECKS = {
    "traefik": check_traefik, "kong": check_kong, "portainer": check_portainer, "swarmpit": check_swarmpit,
    "keycloak": check_keycloak, "authelia": check_authelia, "postgres": check_postgres, "mariadb": check_mariadb,
    "redis": lambda: check_cache("redis"), "valkey": lambda: check_cache("valkey"),
    "rustfs": check_rustfs, "garage": check_garage, "rabbitmq": check_rabbitmq, "nats": check_nats,
    "uptimekuma": check_uptimekuma, "beszel": check_beszel,
}

if __name__ == "__main__":
    print(f"Checking {', '.join(APPS)} on {DOMAIN} (from {'the first manager' if ON_LEADER else 'here, over SSH'})\n")
    check_swarm()
    for app in APPS:
        try:
            CHECKS[app]()
        except Exception as e:  # a crash in one check must not hide the others
            check(f"{app} check ran", False, repr(e))
    failed = [name for name, ok in results if not ok]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    sys.exit(1 if failed else 0)
