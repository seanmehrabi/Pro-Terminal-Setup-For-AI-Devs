#!/usr/bin/env bash
# Optional AI workstation installer — not run by setup_pro_bash.sh automatically.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

if [[ "${EUID:-$(id -u)}" -eq 0 ]] && [[ -n "${SUDO_USER:-}" || "${USER:-root}" == "root" ]]; then
  echo "Do not run setup_ai.sh with sudo — configure your user account, not root." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found in PATH." >&2
  exit 1
fi

cmd="help"
profiles=()
positional=()
all_flag=0
yes_flag=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      cmd="help"
      shift
      ;;
    --list)
      cmd="list"
      shift
      ;;
    --check)
      cmd="check"
      shift
      ;;
    --dry-run)
      cmd="dry-run"
      shift
      ;;
    --all)
      all_flag=1
      shift
      ;;
    --profile)
      [[ $# -ge 2 ]] || { echo "Missing value for --profile" >&2; exit 2; }
      profiles+=("$2")
      shift 2
      ;;
    --update)
      cmd="update"
      shift
      ;;
    --repair)
      cmd="repair"
      shift
      ;;
    --uninstall)
      cmd="uninstall"
      shift
      ;;
    --yes)
      yes_flag=1
      shift
      ;;
    install|update|repair|uninstall|list|check|status|dry-run|help|recommend-models)
      cmd="$1"
      shift
      ;;
    --*)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
    *)
      positional+=("$1")
      shift
      ;;
  esac
done

args=("$cmd")
if [[ "$yes_flag" -eq 1 ]]; then
  args+=("--yes")
fi
if [[ "$all_flag" -eq 1 ]]; then
  args+=("--all")
fi
# Bash 3.2 (macOS) errors on "${empty[@]}" under set -u.
if [[ ${#profiles[@]} -gt 0 ]]; then
  for p in "${profiles[@]}"; do
    args+=("--profile" "$p")
  done
fi
if [[ ${#positional[@]} -gt 0 ]]; then
  args+=("${positional[@]}")
fi

cd "$REPO_ROOT"
python3 -m ai "${args[@]}"
exit $?
