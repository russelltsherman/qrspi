#!/usr/bin/env bash
# template.sh — Canonical starter script demonstrating structural conventions.
# Copy and adapt this file when creating a new bash script.
#
# Structure:
#   1. Shebang + strict mode
#   2. Constants
#   3. Helper functions (logging, cleanup)
#   4. Command functions (one per subcommand)
#   5. Main dispatcher

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

readonly SCRIPT_NAME="${0##*/}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
readonly VERSION="0.1.0"

# Export SCRIPT_DIR so subprocesses can locate sibling files.
export SCRIPT_DIR

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

log_info() {
  printf '[INFO]  %s\n' "$*" >&2
}

log_warn() {
  printf '[WARN]  %s\n' "$*" >&2
}

log_error() {
  printf '[ERROR] %s\n' "$*" >&2
}

cleanup() {
  # Remove temp files, restore state, etc.
  # This function is called by the EXIT trap.
  :
}

trap cleanup EXIT

# ---------------------------------------------------------------------------
# Command functions
# ---------------------------------------------------------------------------

cmd_deploy() {
  local target="${1:?Usage: ${SCRIPT_NAME} deploy <target>}"
  log_info "Deploying to ${target}..."
  # Implementation here
}

cmd_status() {
  log_info "Checking status..."
  # Implementation here
}

cmd_help() {
  cat <<EOF
Usage: ${SCRIPT_NAME} <command> [options]

Commands:
  deploy <target>   Deploy to the specified target
  status            Show current status
  help              Show this help message
  version           Show version

Options:
  -v, --verbose     Enable verbose output
  -h, --help        Show this help message
EOF
}

cmd_version() {
  printf '%s %s\n' "${SCRIPT_NAME}" "${VERSION}"
}

# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

main() {
  if [[ $# -eq 0 ]]; then
    cmd_help
    exit 1
  fi

  local command="$1"
  shift

  case "${command}" in
    deploy)  cmd_deploy "$@" ;;
    status)  cmd_status "$@" ;;
    help | --help | -h)    cmd_help ;;
    version | --version)   cmd_version ;;
    *)
      log_error "Unknown command: ${command}"
      cmd_help
      exit 1
      ;;
  esac
}

main "$@"
