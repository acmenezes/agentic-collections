#!/usr/bin/env python3
"""Apply RBAC and extract SA tokens for cluster-report setup.

Called by build-kubeconfig.sh --setup mode.
Requires: python3 (stdlib only), oc or kubectl in PATH.

Usage:
    python3 setup-clusters.py <kube_cmd> <rbac_manifest> <sa_namespace> \
        <secret_name> <inventory_file> <existing_clusters_json> <ctx1> [ctx2 ...]
"""

import subprocess, sys, json, time, os, base64

kube_cmd = sys.argv[1]
rbac_manifest = sys.argv[2]
sa_namespace = sys.argv[3]
secret_name = sys.argv[4]
inventory_file = sys.argv[5]
existing_clusters = json.loads(sys.argv[6])
contexts = sys.argv[7:]

# Index existing clusters by name for dedup
existing_by_name = {c["name"]: c for c in existing_clusters}

results = {"setup": [], "errors": []}

for ctx in contexts:
    print(f"--- {ctx} ---")

    # Get server URL for this context
    try:
        server = subprocess.check_output(
            [kube_cmd, "config", "view", "-o",
             f"jsonpath={{.clusters[?(@.name==\"{ctx}\")].cluster.server}}"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()

        if not server:
            # Try matching by context's cluster reference
            cluster_ref = subprocess.check_output(
                [kube_cmd, "config", "view", "-o",
                 f"jsonpath={{.contexts[?(@.name==\"{ctx}\")].context.cluster}}"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()
            if cluster_ref:
                server = subprocess.check_output(
                    [kube_cmd, "config", "view", "-o",
                     f"jsonpath={{.clusters[?(@.name==\"{cluster_ref}\")].cluster.server}}"],
                    text=True, stderr=subprocess.DEVNULL
                ).strip()
    except subprocess.CalledProcessError:
        results["errors"].append(f"{ctx}: failed to get server URL")
        print(f"  SKIP: cannot determine server URL")
        continue

    if not server:
        results["errors"].append(f"{ctx}: no server URL found in kubeconfig")
        print(f"  SKIP: no server URL")
        continue

    # Check connectivity
    try:
        subprocess.run(
            [kube_cmd, "cluster-info", "--context", ctx],
            capture_output=True, text=True, timeout=15, check=True
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        results["errors"].append(f"{ctx}: cluster unreachable or auth expired")
        print(f"  SKIP: cluster unreachable (try 'oc login {server}' first)")
        continue

    print(f"  Server: {server}")

    # Apply RBAC manifest
    print(f"  Applying RBAC...")
    try:
        subprocess.run(
            [kube_cmd, "apply", "-f", rbac_manifest, "--context", ctx],
            capture_output=True, text=True, timeout=30, check=True
        )
    except subprocess.CalledProcessError as e:
        results["errors"].append(f"{ctx}: RBAC apply failed: {e.stderr.strip()}")
        print(f"  FAIL: RBAC apply failed: {e.stderr.strip()}")
        continue

    # Wait for token to be populated (up to 15 seconds)
    print(f"  Waiting for token...")
    token = ""
    for attempt in range(15):
        try:
            token = subprocess.check_output(
                [kube_cmd, "get", "secret", secret_name,
                 "-n", sa_namespace, "--context", ctx,
                 "-o", "jsonpath={.data.token}"],
                text=True, stderr=subprocess.DEVNULL, timeout=10
            ).strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

        if token:
            break
        time.sleep(1)

    if not token:
        results["errors"].append(f"{ctx}: token not populated after 15s")
        print(f"  FAIL: token Secret not populated")
        continue

    # Decode base64 token
    try:
        decoded_token = base64.b64decode(token).decode("utf-8")
    except Exception:
        decoded_token = token  # might already be decoded

    # Add to inventory
    entry = {
        "name": ctx,
        "api_url": server,
        "token": decoded_token
    }
    existing_by_name[ctx] = entry
    results["setup"].append(ctx)
    print(f"  OK: token extracted")

# Write inventory
all_clusters = list(existing_by_name.values())
inventory = {"clusters": all_clusters}

with open(inventory_file, "w") as f:
    json.dump(inventory, f, indent=2)
os.chmod(inventory_file, 0o600)

print("")
print("=" * 50)
print(f"Setup complete: {len(results['setup'])} succeeded, {len(results['errors'])} failed")
if results["errors"]:
    print(f"Errors:")
    for e in results["errors"]:
        print(f"  - {e}")
print(f"Inventory written to: {inventory_file}")
print("")
print("Next step:")
print(f"  bash build-kubeconfig.sh --build --clusters {inventory_file} --verify")

# Output JSON summary to stderr for scripting
json.dump(results, sys.stderr, indent=2)
