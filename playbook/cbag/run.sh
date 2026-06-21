#!/usr/bin/env bash
# DGX Spark playbook entrypoint — delegates to the canonical CBAG run script.
set -euo pipefail
exec "$(cd "$(dirname "$0")/../.." && pwd)/scripts/run.sh" "$@"
