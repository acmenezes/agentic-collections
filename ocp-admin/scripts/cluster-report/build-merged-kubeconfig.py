#!/usr/bin/env python3
"""Build a merged kubeconfig from a clusters inventory file.

Called by build-kubeconfig.sh --build mode.
Requires: python3 (stdlib only), oc or kubectl in PATH.

Usage:
    python3 build-merged-kubeconfig.py <kube_cmd> <clusters_file> <output_file> <verify>

    verify: "True" or "False"
"""

import json, sys, os, subprocess

kube_cmd = sys.argv[1]
clusters_file = sys.argv[2]
output_file = sys.argv[3]
verify = sys.argv[4] == "True"

with open(clusters_file) as f:
    config = json.load(f)

clusters = config.get("clusters", [])
if not clusters:
    print('{"error": "No clusters in inventory file"}', file=sys.stderr)
    sys.exit(1)

env = {**os.environ, "KUBECONFIG": output_file}
errors = []
success = 0

for c in clusters:
    name = c.get("name", "")
    api_url = c.get("api_url", "")

    if not name or not api_url:
        errors.append(f"Entry missing name or api_url: {c}")
        continue

    # Resolve token
    token = None
    if "token_env" in c:
        token = os.environ.get(c["token_env"])
        if not token:
            errors.append(f"{name}: env var {c['token_env']} not set")
            continue
    elif "token" in c:
        token = c["token"]
    else:
        errors.append(f"{name}: no token or token_env specified")
        continue

    # Set cluster
    ca_args = []
    if "ca_cert" in c and c["ca_cert"]:
        ca_args = ["--certificate-authority", c["ca_cert"]]
    else:
        ca_args = ["--insecure-skip-tls-verify=true"]

    try:
        subprocess.run(
            [kube_cmd, "config", "set-cluster", name,
             "--server", api_url] + ca_args,
            check=True, capture_output=True, env=env
        )
    except subprocess.CalledProcessError as e:
        errors.append(f"{name}: set-cluster failed: {e.stderr.decode().strip()}")
        continue

    # Set credentials
    try:
        subprocess.run(
            [kube_cmd, "config", "set-credentials", f"{name}-reporter",
             "--token", token],
            check=True, capture_output=True, env=env
        )
    except subprocess.CalledProcessError as e:
        errors.append(f"{name}: set-credentials failed: {e.stderr.decode().strip()}")
        continue

    # Set context
    try:
        subprocess.run(
            [kube_cmd, "config", "set-context", name,
             "--cluster", name,
             "--user", f"{name}-reporter"],
            check=True, capture_output=True, env=env
        )
    except subprocess.CalledProcessError as e:
        errors.append(f"{name}: set-context failed: {e.stderr.decode().strip()}")
        continue

    # Set first successful context as current-context (required by MCP server)
    if success == 0:
        subprocess.run(
            [kube_cmd, "config", "use-context", name],
            check=False, capture_output=True, env=env
        )

    success += 1

# Verify if requested
verify_results = {}
if verify and success > 0:
    print(f"Verifying {success} context(s)...")
    for c in clusters:
        name = c.get("name", "")
        if not name:
            continue
        try:
            subprocess.run(
                [kube_cmd, "cluster-info", "--context", name],
                capture_output=True, text=True, timeout=15, check=True, env=env
            )
            verify_results[name] = "ok"
            print(f"  {name}: OK")
        except subprocess.TimeoutExpired:
            verify_results[name] = "timeout"
            errors.append(f"{name}: verification timed out")
            print(f"  {name}: TIMEOUT")
        except subprocess.CalledProcessError as e:
            verify_results[name] = "failed"
            errors.append(f"{name}: verification failed (likely expired token)")
            print(f"  {name}: FAILED (re-run --setup for this cluster)")

result = {
    "clusters_configured": success,
    "clusters_failed": len(errors),
    "kubeconfig": output_file,
    "errors": errors
}
if verify:
    result["verification"] = verify_results

print("")
print(json.dumps(result, indent=2))

if success == 0:
    sys.exit(1)
