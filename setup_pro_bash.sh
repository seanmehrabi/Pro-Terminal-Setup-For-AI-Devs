#!/usr/bin/env bash
# Pro terminal bootstrap — one identical zsh experience on macOS and Ubuntu/WSL.
#
# What you get: Oh My Zsh + powerlevel10k (rainbow preset, no wizard needed),
# fish-style autosuggestions, fzf-powered tab completion, syntax highlighting,
# and a curated modern CLI toolbox (eza, bat, ripgrep, fd, fzf, zoxide, delta).
#
# Usage: bash setup_pro_bash.sh [--brew] [--reinstall] [--update]   (see --help)
# Never run with sudo. Steps are checkpointed — if a run fails, re-run the same
# command and it resumes at the failed step. Log: ~/.cache/pro-terminal-setup/
#
# CRLF self-heal: a Windows checkout gives this file \r line endings, which makes
# bash choke on the next line ("set: pipefail: invalid option name"). Re-run a
# stripped copy instead. Keep the check on ONE line so that when the file *does*
# have CRLF, the stray \r lands harmlessly inside this trailing comment.
if [ -f "$0" ] && grep -q $'\r' "$0" 2>/dev/null; then printf '\033[1;33m!!\033[0m Fixing CRLF line endings and re-running...\n' >&2; _lf="$(mktemp)"; tr -d '\r' <"$0" >"$_lf"; PTS_SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)" bash "$_lf" "$@"; _rc=$?; rm -f "$_lf"; exit "$_rc"; fi # one line on purpose

set -Eeuo pipefail

OS="$(uname -s)"
IS_WSL=0
[[ "$OS" == "Linux" ]] && grep -qi microsoft /proc/version 2>/dev/null && IS_WSL=1

MARKER_BEGIN="# >>> pro-terminal-setup >>>"
MARKER_END="# <<< pro-terminal-setup <<<"
TOP_BEGIN="# >>> pro-terminal-setup:top >>>"
TOP_END="# <<< pro-terminal-setup:top <<<"
ZSHRC="${ZDOTDIR:-$HOME}/.zshrc"
# PTS_SOURCE_DIR survives the CRLF re-exec, where $0 points at a temp copy.
REPO_DIR="${PTS_SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)}"
LINUXBREW=/home/linuxbrew/.linuxbrew/bin/brew

STATE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/pro-terminal-setup"
STATE_FILE="$STATE_DIR/completed-steps"
LOG_FILE="$STATE_DIR/setup.log"
SUDO="sudo"
MODE="fresh install"
CURRENT_STEP="startup"
STEP_NO=0
TOTAL_STEPS=9
CURL_INSECURE=""

usage() {
    cat <<'EOF'
Pro terminal bootstrap — one identical zsh experience on macOS and Ubuntu/WSL.

Usage:
  bash setup_pro_bash.sh [options]

Options:
  --brew        Linux: install/use Homebrew for the CLI toolbox — same current
                tool versions as macOS (recommended on WSL; apt lags on eza/fzf)
  --reinstall   Back up and remove an existing Oh My Zsh install, plugins and
                prompt preset first, then install everything clean
  --update        Refresh an existing install in place without asking
  --insecure-ssl  LAST RESORT for broken TLS environments: disable certificate
                  verification for this run's downloads. Try without it first —
                  the script auto-repairs the CA store and, on WSL, imports the
                  Windows certificate store (fixes corporate SSL inspection).
  -h, --help      Show this help

Recovery: every step is checkpointed. If a run fails, fix the cause it printed
and re-run the same command — completed steps are skipped automatically.
Progress + full log live in ~/.cache/pro-terminal-setup/.

Ships: Oh My Zsh + powerlevel10k rainbow preset (no wizard), fzf-tab fuzzy
completion, autosuggestions, syntax highlighting, eza/bat/ripgrep/fd/fzf/
zoxide/delta, MesloLGS NF font handling, and a managed ~/.zshrc block.
EOF
}

FORCE_BREW=0
REINSTALL=0
UPDATE_ONLY=0
INSECURE_SSL=0
RERUN_FLAGS=""
for arg in "$@"; do
    case "$arg" in
        --brew) FORCE_BREW=1; RERUN_FLAGS+=" --brew" ;;
        --reinstall) REINSTALL=1 ;;
        --update) UPDATE_ONLY=1 ;;
        --insecure-ssl) INSECURE_SSL=1; RERUN_FLAGS+=" --insecure-ssl" ;;
        -h|--help) usage; exit 0 ;;
        *) printf 'Unknown option: %s (try --help)\n' "$arg" >&2; exit 2 ;;
    esac
done
if [[ "$REINSTALL" == 1 && "$UPDATE_ONLY" == 1 ]]; then
    printf -- '--reinstall and --update are mutually exclusive.\n' >&2
    exit 2
fi

log()  { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

# ------------------------------------------------- recovery & checkpoints ---
# Every step is recorded in $STATE_FILE when it completes. A failed run keeps
# the file, so re-running skips finished steps and resumes at the failure.
# A successful run deletes it.

step_done() { grep -qxF "$1" "$STATE_FILE" 2>/dev/null; }
mark_done() { printf '%s\n' "$1" >> "$STATE_FILE"; }

run_step() {
    local name="$1" fn="$2"
    STEP_NO=$((STEP_NO + 1))
    CURRENT_STEP="$name"
    if step_done "$name"; then
        log "[${STEP_NO}/${TOTAL_STEPS}] ${name}: completed in a previous run — skipping."
        return 0
    fi
    log "[${STEP_NO}/${TOTAL_STEPS}] ${name}..."
    "$fn"
    mark_done "$name"
}

on_error() {
    local code=$? line="$1" done_count=0
    [[ -f "$STATE_FILE" ]] && done_count="$(grep -c . "$STATE_FILE" 2>/dev/null || echo 0)"
    {
        printf '\n\033[1;31m✖ Setup failed\033[0m during step: %s (line %s, exit code %s)\n' \
            "$CURRENT_STEP" "$line" "$code"
        [[ -f "$LOG_FILE" ]] && printf '  Full log:  %s\n' "$LOG_FILE"
        printf '  Progress saved: %s completed step(s) will be skipped next time.\n' "$done_count"
        printf '  Fix the problem shown above, then resume with the same command:\n'
        printf '      bash setup_pro_bash.sh%s\n' "$RERUN_FLAGS"
        printf '  Or start completely clean:  bash setup_pro_bash.sh --reinstall\n\n'
    } >&2
}
trap 'on_error $LINENO' ERR

init_logging() {
    mkdir -p "$STATE_DIR" || die "Cannot create $STATE_DIR (check permissions on ~/.cache)"
    printf '\n===== run: %s | mode pending =====\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
    # Mirror everything the user sees into the log.
    exec > >(tee -a "$LOG_FILE") 2>&1
}

# ------------------------------------------------------------- ssl trust ---
# Corporate proxies (Zscaler, Netskope, ...) and minimal WSL images break TLS
# with: curl: (60) SSL certificate problem: unable to get local issuer cert.
# Fix it properly instead of bypassing: repair the Linux CA store, then (WSL)
# import the Windows certificate store — Windows already trusts the corporate
# root CA, Linux just hasn't heard of it.

ssl_probe() {
    curl $CURL_INSECURE -fsSL --max-time 15 -o /dev/null https://github.com
}

repair_ca_store() {
    [[ "$OS" == "Linux" ]] || return 1
    log "Repairing the system certificate store (ca-certificates)..."
    # apt talks plain http to Ubuntu mirrors, so it works even while TLS is broken.
    $SUDO apt-get update -qq || warn "apt-get update reported errors; continuing."
    $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y --reinstall ca-certificates
    $SUDO update-ca-certificates --fresh >/dev/null
}

import_windows_cas() {
    [[ "$IS_WSL" == 1 ]] || return 1
    command -v powershell.exe >/dev/null 2>&1 || return 1
    log "Importing trusted root certificates from Windows (fixes corporate SSL inspection)..."
    local pem="$STATE_DIR/windows-root-cas.pem"
    # PowerShell reads the Windows cert store; we convert to PEM for Linux.
    (cd /mnt/c 2>/dev/null || cd /; powershell.exe -NoProfile -NonInteractive -Command \
        'Get-ChildItem -Path Cert:\LocalMachine\Root, Cert:\CurrentUser\Root | Sort-Object Thumbprint -Unique | ForEach-Object { "-----BEGIN CERTIFICATE-----"; [Convert]::ToBase64String($_.RawData, "InsertLineBreaks"); "-----END CERTIFICATE-----" }') \
        2>/dev/null | tr -d '\r' > "$pem" || return 1
    local n=0
    n="$(grep -c 'BEGIN CERTIFICATE' "$pem" 2>/dev/null)" || n=0
    if [[ "$n" -eq 0 ]]; then
        warn "Could not export certificates from Windows."
        return 1
    fi
    log "Exported $n Windows root certificates; adding them to the Linux trust store..."
    $SUDO mkdir -p /usr/local/share/ca-certificates
    $SUDO cp "$pem" /usr/local/share/ca-certificates/windows-host-roots.crt
    $SUDO update-ca-certificates >/dev/null
}

ensure_ssl_trust() {
    CURRENT_STEP="ssl-trust"
    command -v curl >/dev/null 2>&1 || return 0   # curl arrives with the packages step

    if [[ "$INSECURE_SSL" == 1 ]]; then
        warn "--insecure-ssl: TLS certificate verification is DISABLED for this run's downloads."
        warn "Only acceptable on a network you trust. Remove the flag once IT gives you the CA."
        CURL_INSECURE="-k"
        export GIT_SSL_NO_VERIFY=true
        return 0
    fi

    local rc=0
    ssl_probe || rc=$?
    [[ "$rc" -eq 0 ]] && return 0

    case "$rc" in
        35|51|58|60|77|83|90)  # TLS-layer failures
            warn "TLS trust problem detected (curl exit $rc) — fixing it automatically..."
            ;;
        *)
            die "Cannot reach github.com (curl exit $rc) — check your network/proxy/VPN and re-run."
            ;;
    esac

    if repair_ca_store && ssl_probe; then
        log "Fixed: certificate store repaired."
        return 0
    fi
    if import_windows_cas && ssl_probe; then
        log "Fixed: Windows root certificates imported — the corporate proxy is now trusted."
        return 0
    fi

    die "TLS verification still fails after automatic repairs. Remaining causes & fixes:
  - Your proxy's root CA isn't in Windows either. Get the CA file (.crt/.pem) from IT, then:
        sudo cp your-ca.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates
  - WSL clock drift (certificate 'not yet valid'): run  sudo hwclock -s  and re-run.
  - Last resort on a trusted network:  bash setup_pro_bash.sh${RERUN_FLAGS} --insecure-ssl"
}

# -------------------------------------------------------------- preflight ---
# Fail fast, with a precise fix, before anything is modified.

preflight() {
    CURRENT_STEP="preflight"

    # Root / sudo policy: never install into root's HOME by accident.
    if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
        if [[ -n "${SUDO_USER:-}" ]]; then
            die "Don't run this with sudo — it would configure root's shell, not yours.
       Run it as your normal user; it will ask for sudo only where needed:
           bash setup_pro_bash.sh${RERUN_FLAGS}"
        fi
        # Genuinely root (e.g. a container): no sudo needed.
        SUDO=""
        [[ "$FORCE_BREW" == 1 ]] && die "Homebrew refuses to run as root. Re-run as a normal user, or drop --brew."
        warn "Running as root: installing for root's HOME."
    elif [[ "$OS" == "Linux" ]]; then
        command -v sudo >/dev/null 2>&1 \
            || die "sudo is required for apt. As root run: apt-get install -y sudo && usermod -aG sudo $USER"
        log "Checking sudo access (you may be asked for your password)..."
        sudo -v || die "sudo authentication failed. Ask your admin for sudo rights, then re-run."
    fi

    # File permissions: catch the classic 'sudo edited my dotfiles' trap early.
    local path
    for path in "$ZSHRC" "$HOME/.oh-my-zsh" "$HOME/.p10k.zsh" "$HOME/.zshrc.local"; do
        if [[ -e "$path" && ! -w "$path" ]]; then
            die "$path is not writable by you (owned by root?). Fix it, then re-run:
           $([[ -n "$SUDO" ]] && printf 'sudo ')chown -R \"\$USER\" \"$path\""
        fi
    done

    # macOS needs Homebrew before anything else.
    if [[ "$OS" == "Darwin" ]] && ! command -v brew >/dev/null 2>&1; then
        die "Homebrew not found. Install it first: https://brew.sh"
    fi

    # Network + TLS: every install path needs GitHub over https. This repairs
    # broken certificate stores / corporate SSL inspection automatically.
    ensure_ssl_trust
}

# ---------------------------------------------------- update vs reinstall ---

detect_existing() {
    [[ -d "$HOME/.oh-my-zsh" ]] || [[ -f "$HOME/.p10k.zsh" ]] \
        || grep -qF "$MARKER_BEGIN" "$ZSHRC" 2>/dev/null
}

# Full reinstall: everything is BACKED UP (never deleted), then reinstalled
# clean. ~/.zshrc and ~/.zshrc.local stay in place; the pipeline refreshes them.
do_reinstall() {
    local stamp backup path
    stamp="$(date +%Y%m%d-%H%M%S)"
    backup="$HOME/.pro-terminal-setup-backup-${stamp}"
    mkdir -p "$backup"
    log "Full reinstall: moving the previous installation to $backup"
    for path in "$HOME/.oh-my-zsh" "$HOME/.p10k.zsh"; do
        [[ -e "$path" ]] && mv "$path" "$backup/$(basename "$path")"
    done
    [[ -f "$ZSHRC" ]] && cp "$ZSHRC" "$backup/zshrc"
    rm -f "$STATE_FILE"
    log "To roll back later: restore from $backup"
}

choose_mode() {
    MODE="fresh install"
    detect_existing || return 0
    MODE="update"

    if [[ "$REINSTALL" == 1 ]]; then
        MODE="full reinstall"
        do_reinstall
        return 0
    fi
    if [[ "$UPDATE_ONLY" == 1 ]]; then
        log "Existing installation found — updating in place."
        return 0
    fi
    if [[ ! -t 0 ]]; then
        log "Existing installation found — updating in place (pass --reinstall for a clean start)."
        return 0
    fi

    printf '\n\033[1;33m!!\033[0m An existing installation was detected (Oh My Zsh / prompt config present).\n'
    printf '   [U]pdate in place  - refresh tools and config, keep everything else  (default, safe)\n'
    printf '   [R]einstall fresh  - back up the old install, then set up completely clean\n'
    printf '   [Q]uit             - change nothing\n'
    local ans=""
    read -r -p "   Choose [U/r/q]: " ans || true
    ans="$(printf '%s' "$ans" | tr '[:upper:]' '[:lower:]')"   # bash 3.2-safe lowercase
    case "$ans" in
        r*) MODE="full reinstall"; do_reinstall ;;
        q*) log "Nothing changed. Bye."; exit 0 ;;
        *)  log "Updating in place." ;;
    esac
}

backup_file() {
    local file="$1"
    if [[ -f "$file" ]]; then
        local stamp
        stamp="$(date +%Y%m%d-%H%M%S)"
        cp "$file" "${file}.bak.${stamp}"
        log "Backed up $file -> ${file}.bak.${stamp}"
    fi
}

apt_available() { apt-cache show "$1" >/dev/null 2>&1; }

# ---------------------------------------------------------------- packages --

use_brew() {
    if [[ "$OS" == "Darwin" ]]; then
        command -v brew >/dev/null 2>&1 || die "Homebrew not found. Install it first: https://brew.sh"
        return 0
    fi
    # Linux: use brew when it's already there or explicitly requested.
    if command -v brew >/dev/null 2>&1; then
        return 0
    fi
    if [[ -x "$LINUXBREW" ]]; then
        eval "$("$LINUXBREW" shellenv)"
        return 0
    fi
    if [[ "$FORCE_BREW" == 1 ]]; then
        install_linuxbrew
        return 0
    fi
    return 1
}

install_linuxbrew() {
    log "Installing Homebrew for Linux (this may take a few minutes)..."
    $SUDO apt-get update
    $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y build-essential procps curl file git
    NONINTERACTIVE=1 bash -c \
        "$(curl $CURL_INSECURE -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    [[ -x "$LINUXBREW" ]] || die "Homebrew install did not produce $LINUXBREW"
    eval "$("$LINUXBREW" shellenv)"
}

install_packages() {
    # Same modern toolbox on both platforms.
    local tools=(tmux fzf bat eza vim htop ripgrep fd jq zoxide git-delta gh wget)

    if use_brew; then
        # zsh/git/curl stay system-level (apt / macOS built-ins) so chsh and
        # /etc/shells keep working; brew only manages the toolbox.
        if [[ "$OS" == "Linux" ]]; then
            log "Installing base packages via apt..."
            $SUDO apt-get update
            $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y zsh git curl
        else
            log "Updating Homebrew..."
            brew update
        fi
        log "Installing CLI toolbox via Homebrew..."
        brew install "${tools[@]}"
    elif [[ -f /etc/debian_version ]]; then
        log "Installing via apt (tip: --brew gets newer tools via Homebrew)..."
        $SUDO apt-get update

        local apt_pkgs=(zsh git curl) pkg apt_name
        for pkg in "${tools[@]}"; do
            apt_name="$pkg"
            [[ "$pkg" == "fd" ]] && apt_name="fd-find"
            if apt_available "$apt_name"; then
                apt_pkgs+=("$apt_name")
            else
                warn "Not in apt on this release: $apt_name (use --brew to get it)"
            fi
        done
        $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y "${apt_pkgs[@]}"
    else
        die "Unsupported OS. This script supports macOS and Debian/Ubuntu (incl. WSL)."
    fi
}

# -------------------------------------------------------- zsh framework -----

install_oh_my_zsh() {
    if [[ -d "$HOME/.oh-my-zsh" ]]; then
        log "Oh My Zsh already installed."
        return
    fi
    log "Installing Oh My Zsh..."
    RUNZSH=no CHSH=no KEEP_ZSHRC=yes \
        sh -c "$(curl $CURL_INSECURE -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
}

install_powerlevel10k() {
    local dest="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k"
    if [[ -d "$dest" ]]; then
        log "powerlevel10k already installed."
        return
    fi
    log "Installing powerlevel10k..."
    git clone --depth=1 https://github.com/romkatv/powerlevel10k.git "$dest"
}

install_plugin() {
    local base="$1" name="$2" url="$3"
    if [[ -d "$base/$name" ]]; then
        log "Plugin $name already installed."
    else
        log "Installing plugin $name..."
        git clone --depth=1 "$url" "$base/$name"
    fi
}

install_plugins() {
    local base="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins"
    mkdir -p "$base"

    install_plugin "$base" zsh-autosuggestions     https://github.com/zsh-users/zsh-autosuggestions
    install_plugin "$base" zsh-syntax-highlighting https://github.com/zsh-users/zsh-syntax-highlighting
    install_plugin "$base" zsh-completions         https://github.com/zsh-users/zsh-completions
    install_plugin "$base" fzf-tab                 https://github.com/Aloxaf/fzf-tab
}

# Ship the repo's powerlevel10k preset so the prompt looks right on first
# launch — no wizard required. Never clobber an existing ~/.p10k.zsh.
install_p10k_config() {
    if [[ -f "$HOME/.p10k.zsh" ]]; then
        log "Keeping existing ~/.p10k.zsh (run 'p10k configure' to restyle)."
        return
    fi
    if [[ -f "$REPO_DIR/config/p10k.zsh" ]]; then
        cp "$REPO_DIR/config/p10k.zsh" "$HOME/.p10k.zsh"
        log "Installed powerlevel10k preset -> ~/.p10k.zsh"
    else
        warn "config/p10k.zsh not found; powerlevel10k will run its wizard on first launch."
    fi
}

# ------------------------------------------------------------------ fonts ---

install_fonts() {
    if [[ "$OS" == "Darwin" ]]; then
        log "Installing MesloLGS Nerd Font..."
        brew install --cask font-meslo-lg-nerd-font \
            || warn "Font cask install failed; install MesloLGS NF manually."
        return
    fi

    [[ "$IS_WSL" == 1 ]] || return 0

    # Fonts must be installed on the Windows side. Download them somewhere the
    # user can reach and finish with two clicks.
    local win_home=""
    if command -v cmd.exe >/dev/null 2>&1; then
        win_home="$(cd /mnt/c 2>/dev/null && cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r' || true)"
        [[ -n "$win_home" ]] && win_home="$(wslpath "$win_home" 2>/dev/null || true)"
    fi
    local dest="${win_home:-/mnt/c/Users/Public}/Downloads/MesloLGS-NF"
    if [[ ! -d "$(dirname "$dest")" ]]; then
        warn "Could not find a Windows Downloads folder; install MesloLGS NF manually:"
        warn "  https://github.com/romkatv/powerlevel10k#fonts"
        return 0
    fi

    mkdir -p "$dest"
    local base="https://github.com/romkatv/powerlevel10k-media/raw/master"
    local style ok=1
    for style in "Regular" "Bold" "Italic" "Bold%20Italic"; do
        local file="MesloLGS NF ${style//%20/ }.ttf"
        if [[ -f "$dest/$file" ]]; then
            continue
        fi
        curl $CURL_INSECURE -fsSL -o "$dest/$file" "$base/MesloLGS%20NF%20${style}.ttf" || ok=0
    done
    if [[ "$ok" == 1 ]]; then
        log "Fonts downloaded to Windows: $dest"
        log "Finish on Windows: open that folder, select all 4 fonts -> right-click -> Install,"
        log "then set Windows Terminal font to 'MesloLGS NF' (Settings -> Ubuntu -> Appearance)."
    else
        warn "Some font downloads failed; grab them from https://github.com/romkatv/powerlevel10k#fonts"
    fi
}

# ----------------------------------------------------------------- ~/.zshrc --

sources_omz() {
    grep -q 'oh-my-zsh\.sh' "$1" 2>/dev/null
}

# ZSH_THEME, plugins=() and fpath additions only take effect if they are set
# *before* oh-my-zsh.sh is sourced, so insert above that line when it exists.
add_config_line() {
    local file="$1" line="$2" tmp
    if sources_omz "$file"; then
        tmp="$(mktemp)"
        awk -v ins="$line" '
            !inserted && /oh-my-zsh\.sh/ { print ins; inserted=1 }
            { print }
        ' "$file" > "$tmp"
        cat "$tmp" > "$file"   # cat> keeps symlinked dotfiles intact
        rm -f "$tmp"
    else
        printf '\n%s\n' "$line" >> "$file"
    fi
}

# Oh My Zsh is installed with KEEP_ZSHRC=yes, so a pre-existing ~/.zshrc
# (WSL/Ubuntu creates one) is left untouched and never loads the framework.
ensure_omz_bootstrap() {
    local file="$1"
    if sources_omz "$file"; then
        return
    fi
    log "Adding Oh My Zsh bootstrap to $file"
    printf '\nexport ZSH="$HOME/.oh-my-zsh"\nsource "$ZSH/oh-my-zsh.sh"\n' >> "$file"
}

ensure_theme() {
    local file="$1"
    if grep -q '^ZSH_THEME=' "$file" 2>/dev/null; then
        # portable in-place edit
        if sed --version >/dev/null 2>&1; then
            sed -i 's/^ZSH_THEME=.*/ZSH_THEME="powerlevel10k\/powerlevel10k"/' "$file"
        else
            sed -i.bak 's/^ZSH_THEME=.*/ZSH_THEME="powerlevel10k\/powerlevel10k"/' "$file"
            rm -f "${file}.bak"
        fi
    else
        add_config_line "$file" 'ZSH_THEME="powerlevel10k/powerlevel10k"'
    fi
}

ensure_plugins_line() {
    local file="$1"
    # Order matters: fzf-tab after compinit (OMZ handles that), before the
    # widget-wrapping plugins; syntax-highlighting must come last.
    local desired="plugins=(git fzf-tab zsh-autosuggestions zsh-syntax-highlighting)"

    if grep -q '^plugins=(' "$file" 2>/dev/null; then
        # Replace the whole plugins=() assignment, single-line or multiline.
        local tmp
        tmp="$(mktemp)"
        awk -v d="$desired" '
            /^plugins=\(/ && !done { inblk=1 }
            inblk { if (/\)/) { print d; done=1; inblk=0 }; next }
            { print }
        ' "$file" > "$tmp"
        cat "$tmp" > "$file"
        rm -f "$tmp"
    else
        add_config_line "$file" "$desired"
    fi
}

# zsh-completions is used via fpath (its README's recommended Oh My Zsh setup),
# not as a plugin — the plugin form adds its completions after compinit ran.
ensure_completions_fpath() {
    local file="$1"
    local line='fpath+=("${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-completions/src")'
    grep -qF 'zsh-completions/src' "$file" 2>/dev/null && return
    add_config_line "$file" "$line"
}

strip_block() {
    local file="$1" begin="$2" end="$3" tmp
    [[ -f "$file" ]] && grep -qF "$begin" "$file" || return 0
    tmp="$(mktemp)"
    awk -v b="$begin" -v e="$end" '
        $0 == b { skip=1; next }
        $0 == e { skip=0; next }
        !skip { print }
    ' "$file" > "$tmp"
    cat "$tmp" > "$file"
    rm -f "$tmp"
}

# Instant prompt + Homebrew PATH must run before everything else in ~/.zshrc.
write_top_block() {
    local file="$1" tmp
    strip_block "$file" "$TOP_BEGIN" "$TOP_END"
    # Drop leading blank lines so re-runs don't accumulate them under the block.
    tmp="$(mktemp)"
    awk 'NF { seen=1 } seen' "$file" > "$tmp"
    cat "$tmp" > "$file"
    cat > "$tmp" <<'EOF'
# >>> pro-terminal-setup:top >>>
# Homebrew on Linux must be on PATH before anything else uses its tools.
if [[ -x /home/linuxbrew/.linuxbrew/bin/brew && -z "${HOMEBREW_PREFIX:-}" ]]; then
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi
# Powerlevel10k instant prompt — keep at the very top of ~/.zshrc.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi
# <<< pro-terminal-setup:top <<<

EOF
    cat "$file" >> "$tmp"
    cat "$tmp" > "$file"
    rm -f "$tmp"
}

write_managed_block() {
    local file="$1" tmp
    strip_block "$file" "$MARKER_BEGIN" "$MARKER_END"

    # Trim trailing blank lines so re-runs don't accumulate them above the block.
    tmp="$(mktemp)"
    awk '/[^[:space:]]/ { for (i = 0; i < blank; i++) print ""; blank = 0; print; next } { blank++ }' \
        "$file" > "$tmp"
    cat "$tmp" > "$file"
    rm -f "$tmp"

    # Quoted heredoc: everything below lands in ~/.zshrc verbatim and resolves
    # at shell startup, so one block works on macOS, apt and brew installs.
    cat >> "$file" <<'EOF'

# >>> pro-terminal-setup >>>
# Managed by Pro-Terminal-Setup-For-AI-Devs — safe to re-run the installer.

# ---- History: large, shared, de-duplicated ----
HISTSIZE=100000
SAVEHIST=100000
setopt HIST_IGNORE_DUPS HIST_IGNORE_ALL_DUPS HIST_IGNORE_SPACE HIST_REDUCE_BLANKS
setopt SHARE_HISTORY INC_APPEND_HISTORY EXTENDED_HISTORY

# ---- Completion: case-insensitive, colored, fzf-tab UI ----
zstyle ':completion:*' matcher-list 'm:{a-zA-Z-_}={A-Za-z_-}' 'r:|=*' 'l:|=* r:|=*'
zstyle ':completion:*' list-colors "${(s.:.)LS_COLORS}"
zstyle ':completion:*' menu no
zstyle ':completion:*:descriptions' format '[%d]'
zstyle ':fzf-tab:*' fzf-flags '--height=60%' '--border'
zstyle ':fzf-tab:complete:cd:*' fzf-preview 'eza -1 --color=always -- $realpath 2>/dev/null || ls -1 -- $realpath'
zstyle ':fzf-tab:complete:__zoxide_z:*' fzf-preview 'eza -1 --color=always -- $realpath 2>/dev/null || ls -1 -- $realpath'

# ---- Autosuggestions: ghost text from history; accept with Right arrow ----
ZSH_AUTOSUGGEST_STRATEGY=(history completion)
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=244'

# ---- Debian/Ubuntu binary names (bat -> batcat, fd -> fdfind) ----
if command -v batcat >/dev/null 2>&1 && ! command -v bat >/dev/null 2>&1; then
  alias bat='batcat'
fi
if command -v fdfind >/dev/null 2>&1 && ! command -v fd >/dev/null 2>&1; then
  alias fd='fdfind'
fi

# ---- Modern CLI aliases ----
if command -v eza >/dev/null 2>&1; then
  alias ls='eza --group-directories-first --icons=auto'
  alias ll='eza -lah --group-directories-first --git --icons=auto'
  alias la='eza -a --group-directories-first --icons=auto'
  alias lt='eza --tree --level=2 --icons=auto'
else
  alias ll='ls -lah'
  alias la='ls -A'
fi
if command -v bat >/dev/null 2>&1 || alias bat >/dev/null 2>&1; then
  alias cat='bat --paging=never'
  export BAT_THEME='TwoDark'
fi
command -v rg >/dev/null 2>&1 && alias grep='rg'

# ---- Git shortcuts ----
alias gs='git status -sb'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline --graph --decorate -20'
alias gd='git diff'
alias gco='git checkout'

# ---- Navigation ----
alias ..='cd ..'
alias ...='cd ../..'
alias mkdir='mkdir -p'

# ---- fzf: Ctrl-R history, Ctrl-T files, themed picker ----
if command -v fzf >/dev/null 2>&1; then
  if fzf --zsh >/dev/null 2>&1; then
    source <(fzf --zsh)
  elif [[ -f ~/.fzf.zsh ]]; then
    source ~/.fzf.zsh
  elif [[ -f /usr/share/doc/fzf/examples/key-bindings.zsh ]]; then
    source /usr/share/doc/fzf/examples/key-bindings.zsh
    [[ -f /usr/share/doc/fzf/examples/completion.zsh ]] && source /usr/share/doc/fzf/examples/completion.zsh
  fi
  export FZF_DEFAULT_OPTS='--height=60% --layout=reverse --border --info=inline'
  if command -v fd >/dev/null 2>&1; then
    export FZF_DEFAULT_COMMAND='fd --type f --hidden --follow --exclude .git'
  elif command -v fdfind >/dev/null 2>&1; then
    export FZF_DEFAULT_COMMAND='fdfind --type f --hidden --follow --exclude .git'
  fi
  [[ -n "${FZF_DEFAULT_COMMAND:-}" ]] && export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
fi

# ---- Smart directory jumping: z <dir> ----
command -v zoxide >/dev/null 2>&1 && eval "$(zoxide init zsh)"

# ---- Better git paging ----
command -v delta >/dev/null 2>&1 && export GIT_PAGER='delta'

# ---- Editor defaults (override in ~/.zshrc.local) ----
export EDITOR="${EDITOR:-vim}"
export VISUAL="${VISUAL:-$EDITOR}"

# ---- Prompt preset; restyle anytime with: p10k configure ----
[[ -f ~/.p10k.zsh ]] && source ~/.p10k.zsh

# ---- Machine-local overrides ----
[[ -f "$HOME/.zshrc.local" ]] && source "$HOME/.zshrc.local"
# <<< pro-terminal-setup <<<
EOF
}

update_zshrc() {
    log "Updating ${ZSHRC}..."
    [[ -f "$ZSHRC" ]] || touch "$ZSHRC"
    backup_file "$ZSHRC"
    ensure_theme "$ZSHRC"
    ensure_plugins_line "$ZSHRC"
    ensure_completions_fpath "$ZSHRC"
    # After theme/plugins/fpath so those land above the source line, before the
    # managed block so our aliases win over the framework's.
    ensure_omz_bootstrap "$ZSHRC"
    write_top_block "$ZSHRC"
    write_managed_block "$ZSHRC"

    if ! sources_omz "$ZSHRC"; then
        warn "$ZSHRC still does not source oh-my-zsh.sh; the theme will not load."
    fi
}

# ------------------------------------------------------------------- git ----

configure_git() {
    # WSL: stop git from ever writing CRLF into working trees.
    if [[ "$IS_WSL" == 1 ]] && ! git config --global --get core.autocrlf >/dev/null 2>&1; then
        log "Setting git core.autocrlf=input (WSL CRLF protection)..."
        git config --global core.autocrlf input
    fi

    command -v delta >/dev/null 2>&1 || return 0
    if git config --global --get core.pager >/dev/null 2>&1; then
        return 0
    fi
    log "Configuring git to use delta..."
    git config --global core.pager delta
    git config --global interactive.diffFilter 'delta --color-only'
    git config --global delta.navigate true
    git config --global delta.line-numbers true
    git config --global merge.conflictstyle diff3
}

set_default_shell() {
    local zsh_path
    zsh_path="$(command -v zsh)" || { warn "zsh not on PATH; skipping chsh."; return 0; }
    if [[ "${SHELL:-}" == "$zsh_path" ]]; then
        log "Default shell already zsh."
        return
    fi
    if ! grep -qx "$zsh_path" /etc/shells 2>/dev/null; then
        warn "$zsh_path is not in /etc/shells; add it, then run: chsh -s $zsh_path"
        return
    fi
    log "Setting default shell to zsh..."
    if chsh -s "$zsh_path"; then
        log "Default shell changed to $zsh_path"
    else
        warn "Could not change default shell automatically. Run: chsh -s $zsh_path"
    fi
}

print_final() {
    cat <<'EOF'

Setup complete.

Next steps:
  1. Start a fresh shell:            exec zsh
  2. Set your terminal font to "MesloLGS NF"
       macOS: Terminal/iTerm2 profile font
       WSL:   install the 4 fonts from Downloads\MesloLGS-NF, then
              Windows Terminal -> Settings -> Ubuntu -> Appearance -> Font face

Daily drivers:
  TAB        fuzzy-picker completion for commands, paths, git branches...
  Right ->   accept the gray autosuggestion from your history
  Ctrl-R     fuzzy search shell history
  Ctrl-T     fuzzy-insert a file path
  z <dir>    jump to any directory you have visited (zoxide)
  ll / lt    rich file listings and trees (eza)

The prompt ships preconfigured (rainbow powerlevel10k). To restyle: p10k configure
Machine-only tweaks go in ~/.zshrc.local — the managed block never touches it.

EOF
    printf 'Run log: %s\n\n' "$LOG_FILE"
}

main() {
    local flavor="$OS"
    [[ "$IS_WSL" == 1 ]] && flavor="WSL/Ubuntu"

    init_logging
    preflight
    choose_mode
    log "Starting pro terminal setup (${flavor}) — mode: ${MODE}."
    if [[ -s "$STATE_FILE" ]]; then
        log "Resuming a previous run: $(grep -c . "$STATE_FILE") completed step(s) will be skipped."
        log "(Start over instead with: rm $STATE_FILE  — or use --reinstall.)"
    fi

    run_step "packages"       install_packages
    run_step "oh-my-zsh"      install_oh_my_zsh
    run_step "powerlevel10k"  install_powerlevel10k
    run_step "plugins"        install_plugins
    run_step "prompt-preset"  install_p10k_config
    run_step "fonts"          install_fonts
    run_step "zshrc"          update_zshrc
    run_step "git-config"     configure_git
    run_step "default-shell"  set_default_shell

    CURRENT_STEP="finish"
    rm -f "$STATE_FILE"
    print_final
}

main "$@"
