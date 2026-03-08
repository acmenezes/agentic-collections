#!/usr/bin/env bash
# build-kubeconfig.sh — Multi-cluster kubeconfig builder for cluster-report
#
# Two modes:
#   --setup   Apply RBAC and extract SA tokens for clusters you're logged into
#   --build   Build a merged kubeconfig from a clusters inventory file
#
# Usage:
#   bash build-kubeconfig.sh --setup [--all-contexts] [--contexts ctx1,ctx2]
#                            [--output-inventory <path>]
#
#   bash build-kubeconfig.sh --build --clusters <clusters.json>
#                            [--output <path>] [--verify]
#
# Requires: oc or kubectl, python3 (stdlib only)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RBAC_MANIFEST="${SCRIPT_DIR}/cluster-reporter-rbac.yaml"

MODE=""
CLUSTERS_FILE=""
OUTPUT_FILE="/tmp/cluster-report-kubeconfig"
INVENTORY_FILE="${HOME}/.ocp-clusters/clusters.json"
VERIFY=false
ALL_CONTEXTS=false
SELECTED_CONTEXTS=""

# --- Argument parsing ---

usage() {
  cat <<'USAGE'
Usage:
  build-kubeconfig.sh --setup [--all-contexts] [--contexts ctx1,ctx2]
                      [--output-inventory <path>]

  build-kubeconfig.sh --build --clusters <clusters.json>
                      [--output <path>] [--verify]

Modes:
  --setup             Apply RBAC to clusters you're logged into, extract SA tokens,
                      and write a clusters inventory file.
  --build             Read a clusters inventory file and build a merged kubeconfig.

Setup options:
  --all-contexts      Setup all kubeconfig contexts without prompting.
  --contexts c1,c2    Setup only the specified contexts (comma-separated).
  --output-inventory  Path for the clusters inventory file.
                      Default: ~/.ocp-clusters/clusters.json

Build options:
  --clusters <path>   Path to the clusters inventory JSON file (required).
  --output <path>     Path for the generated kubeconfig.
                      Default: /tmp/cluster-report-kubeconfig
  --verify            Test each context after building the kubeconfig.
USAGE
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --setup)            MODE="setup"; shift ;;
    --build)            MODE="build"; shift ;;
    --clusters)         CLUSTERS_FILE="$2"; shift 2 ;;
    --output)           OUTPUT_FILE="$2"; shift 2 ;;
    --output-inventory) INVENTORY_FILE="$2"; shift 2 ;;
    --verify)           VERIFY=true; shift ;;
    --all-contexts)     ALL_CONTEXTS=true; shift ;;
    --contexts)         SELECTED_CONTEXTS="$2"; shift 2 ;;
    -h|--help)          usage ;;
    *)                  echo "Unknown flag: $1" >&2; usage ;;
  esac
done

if [[ -z "$MODE" ]]; then
  echo "Error: specify --setup or --build" >&2
  usage
fi

# --- Helpers ---

KUBE_CMD=""
if command -v oc &>/dev/null; then
  KUBE_CMD="oc"
elif command -v kubectl &>/dev/null; then
  KUBE_CMD="kubectl"
else
  echo '{"error": "Neither oc nor kubectl found in PATH"}' >&2
  exit 1
fi

SA_NAMESPACE="cluster-reporter-system"
SA_NAME="cluster-reporter"
SECRET_NAME="cluster-reporter-token"

# --- Setup mode ---

run_setup() {
  if [[ ! -f "$RBAC_MANIFEST" ]]; then
    echo "Error: RBAC manifest not found at ${RBAC_MANIFEST}" >&2
    exit 1
  fi

  mapfile -t ALL_CTX < <($KUBE_CMD config get-contexts -o name 2>/dev/null)

  if [[ ${#ALL_CTX[@]} -eq 0 ]]; then
    echo '{"error": "No kubeconfig contexts found. Log in to at least one cluster first."}' >&2
    exit 1
  fi

  CONTEXTS_TO_PROCESS=()

  if [[ -n "$SELECTED_CONTEXTS" ]]; then
    IFS=',' read -ra CONTEXTS_TO_PROCESS <<< "$SELECTED_CONTEXTS"
  elif [[ "$ALL_CONTEXTS" == "true" ]]; then
    CONTEXTS_TO_PROCESS=("${ALL_CTX[@]}")
  else
    echo "Available contexts:"
    for i in "${!ALL_CTX[@]}"; do
      echo "  $((i+1)). ${ALL_CTX[$i]}"
    done
    echo ""
    echo "Run with --all-contexts to setup all, or --contexts ctx1,ctx2 to select specific ones."
    exit 0
  fi

  echo "Setting up ${#CONTEXTS_TO_PROCESS[@]} cluster(s)..."
  echo ""

  INVENTORY_DIR="$(dirname "$INVENTORY_FILE")"
  mkdir -p "$INVENTORY_DIR"

  EXISTING_CLUSTERS="[]"
  if [[ -f "$INVENTORY_FILE" ]]; then
    EXISTING_CLUSTERS=$(python3 -c "
import json, sys
with open('${INVENTORY_FILE}') as f:
    data = json.load(f)
json.dump(data.get('clusters', []), sys.stdout)
" 2>/dev/null || echo "[]")
  fi

  python3 "${SCRIPT_DIR}/setup-clusters.py" "$KUBE_CMD" "$RBAC_MANIFEST" "$SA_NAMESPACE" "$SECRET_NAME" "$INVENTORY_FILE" "$EXISTING_CLUSTERS" "${CONTEXTS_TO_PROCESS[@]}"
}

# --- Build mode ---

run_build() {
  if [[ -z "$CLUSTERS_FILE" ]]; then
    echo "Error: --clusters <path> is required for --build mode" >&2
    usage
  fi

  if [[ ! -f "$CLUSTERS_FILE" ]]; then
    echo "{\"error\": \"Clusters file not found: ${CLUSTERS_FILE}\"}" >&2
    exit 1
  fi

  rm -f "$OUTPUT_FILE"
  touch "$OUTPUT_FILE"
  chmod 600 "$OUTPUT_FILE"

  python3 "${SCRIPT_DIR}/build-merged-kubeconfig.py" "$KUBE_CMD" "$CLUSTERS_FILE" "$OUTPUT_FILE" "$VERIFY"

  echo ""
  echo "Kubeconfig written to: ${OUTPUT_FILE}"
  echo ""
  echo "To use with cluster-report:"
  echo "  export KUBECONFIG=${OUTPUT_FILE}"
}

# --- Main ---

case "$MODE" in
  setup) run_setup ;;
  build) run_build ;;
  *)     usage ;;
esac
