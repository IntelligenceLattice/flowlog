#!/usr/bin/env bash
# Runs the toy MCP-doc-host example with flowlog's viewer open.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
flowlog run --config "$HERE/flowlog.config.json" "$HERE/toy_host.py" -- "${1:-How do I rotate an API key?}"
