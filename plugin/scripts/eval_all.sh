#!/usr/bin/env bash
# Thin wrapper so the literal `./scripts/eval_all.sh` AC1 invocation works.
# Delegates verbatim to the Python entrypoint (ref RUS-41 Q4).
set -euo pipefail
exec python3 "$(dirname "$0")/eval_all.py" "$@"
