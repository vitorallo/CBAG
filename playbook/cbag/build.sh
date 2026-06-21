#!/usr/bin/env bash
# DGX Spark playbook entrypoint — delegates to the canonical CBAG build script.
set -euo pipefail
exec "$(cd "$(dirname "$0")/../.." && pwd)/scripts/build.sh" "$@"
