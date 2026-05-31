#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Bash Script Template
# A minimal, ShellCheck-clean script demonstrating all conventions.
# Copy this file as your starting point for any bash script project.
# ============================================================================

# --- Constants ---
readonly SCRIPT_NAME="${0##*/}"
readonly VERSION="1.0.0"

# --- Temp files ---
TEMP_FILES=()

# --- Color helpers (only active when stderr is a TTY) ---
if [[ -t 2 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# --- Logging helpers ---
log()     { echo "${NC}$*${NC}" >&2; }
info()    { echo "${GREEN}[INFO]${NC} $*" >&2; }
warn()    { echo "${YELLOW}[WARN]${NC} $*" >&2; }
die()     { echo "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# --- Cleanup ---
add_temp() { TEMP_FILES+=("$1"); }

cleanup() {
    for f in "${TEMP_FILES[@]}"; do
        rm -f "$f" 2>/dev/null || true
    done
}
trap cleanup EXIT

# --- Dependency checking ---
check_dep() {
    if ! command -v "$1" >/dev/null 2>&1; then
        die "Required command not found: $1"
    fi
}

# --- Usage/Help ---
usage() {
    cat <<EOF
Usage: ${SCRIPT_NAME} <command> [options]

A minimal bash script template demonstrating project conventions.

Commands:
  deploy    Deploy the application
  status    Show current status
  help      Show this help message

Options:
  -v, --verbose    Enable verbose output
  -q, --quiet      Suppress non-error output
  --version        Show version
  --help           Show this help message

Exit Codes:
  0  Success
  1  General error
  2  Bad arguments or unknown command
EOF
}

# --- Command functions ---
cmd_deploy() {
    local config_file="${1:-}"
    local verbose=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --config) config_file="$2"; shift 2 ;;
            -v|--verbose) verbose=true; shift ;;
            -q|--quiet) shift ;;
            *) die "Unknown option: $1" ;;
        esac
    done

    if [[ -z "${config_file}" ]]; then
        die "deploy requires --config <file>"
    fi

    if [[ "${verbose}" == true ]]; then
        info "Deploying from config: ${config_file}"
    else
        info "Deploying..."
    fi
}

cmd_status() {
    local verbose=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -v|--verbose) verbose=true; shift ;;
            *) shift ;;
        esac
    done

    if [[ "${verbose}" == true ]]; then
        info "Status: OK"
    else
        echo "OK"
    fi
}

cmd_help() {
    usage
}

# --- Main ---
main() {
    # Parse global options first
    local positional=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --version) echo "${VERSION}"; exit 0 ;;
            --help)    usage; exit 0 ;;
            -v|--verbose) shift ;;
            -q|--quiet)  shift ;;
            --)          shift; positional+=("$@"); break ;;
            *)           positional+=("$1"); shift ;;
        esac
    done

    # Dispatch subcommand
    local subcmd="${positional[0]:-help}"
    local args=("${positional[@]:1}")

    if declare -f "cmd_${subcmd}" >/dev/null 2>&1; then
        "cmd_${subcmd}" "${args[@]:-}"
    else
        echo "Unknown command: ${subcmd}" >&2
        cmd_help
        exit 2
    fi
}

# --- Entry point ---
main "$@"
