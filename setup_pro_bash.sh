#!/usr/bin/env bash
# Professional terminal bootstrap for macOS and Debian/Ubuntu (incl. WSL).
#
# CRLF self-heal: a Windows checkout gives this file \r line endings, which makes
# bash choke on the next line ("set: pipefail: invalid option name"). Re-run a
# stripped copy instead. Keep the check on ONE line so that when the file *does*
# have CRLF, the stray \r lands harmlessly inside this trailing comment.
if [ -f "$0" ] && grep -q $'\r' "$0" 2>/dev/null; then printf '\033[1;33m!!\033[0m Fixing CRLF line endings and re-running...\n' >&2; _lf="$(mktemp)"; tr -d '\r' <"$0" >"$_lf"; bash "$_lf" "$@"; _rc=$?; rm -f "$_lf"; exit "$_rc"; fi # one line on purpose

set -euo pipefail

OS="$(uname -s)"
MARKER_BEGIN="# >>> pro-terminal-setup >>>"
MARKER_END="# <<< pro-terminal-setup <<<"
ZSHRC="${ZDOTDIR:-$HOME}/.zshrc"

log()  { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

backup_file() {
    local file="$1"
    if [[ -f "$file" ]]; then
        local stamp
        stamp="$(date +%Y%m%d-%H%M%S)"
        cp "$file" "${file}.bak.${stamp}"
        log "Backed up $file -> ${file}.bak.${stamp}"
    fi
}

pkg_available() {
    if [[ "$OS" == "Darwin" ]]; then
        brew info --formula "$1" >/dev/null 2>&1
    else
        apt-cache show "$1" >/dev/null 2>&1
    fi
}

install_packages() {
    local packages=(
        zsh git curl wget tmux fzf bat eza vim htop
        ripgrep fd jq zoxide
    )
    local optional=(git-delta gh)

    if [[ "$OS" == "Darwin" ]]; then
        command -v brew >/dev/null 2>&1 || die "Homebrew not found. Install it first: https://brew.sh"
        log "Updating Homebrew..."
        brew update

        # Homebrew formula names
        local brew_pkgs=(zsh git curl wget tmux fzf bat eza vim htop ripgrep fd jq zoxide git-delta gh)
        brew install "${brew_pkgs[@]}"

        log "Installing MesloLGS Nerd Font..."
        brew install --cask font-meslo-lg-nerd-font || warn "Font cask install failed; install MesloLGS NF manually."
    elif [[ -f /etc/debian_version ]]; then
        log "Updating apt..."
        sudo apt-get update

        local apt_pkgs=()
        local pkg
        for pkg in "${packages[@]}"; do
            # Ubuntu packages bat as bat; binary is often batcat.
            # Older distros may lack eza/fd/zoxide — skip missing ones.
            case "$pkg" in
                fd) pkg="fd-find" ;;
            esac
            if pkg_available "$pkg"; then
                apt_pkgs+=("$pkg")
            else
                warn "Skipping unavailable package: $pkg"
            fi
        done

        for pkg in "${optional[@]}"; do
            local apt_name="$pkg"
            [[ "$pkg" == "git-delta" ]] && apt_name="git-delta"
            if pkg_available "$apt_name"; then
                apt_pkgs+=("$apt_name")
            else
                warn "Optional package not available: $apt_name"
            fi
        done

        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${apt_pkgs[@]}"
    else
        die "Unsupported OS. This script supports macOS and Debian/Ubuntu."
    fi
}

install_oh_my_zsh() {
    if [[ -d "$HOME/.oh-my-zsh" ]]; then
        log "Oh My Zsh already installed."
        return
    fi
    log "Installing Oh My Zsh..."
    RUNZSH=no CHSH=no KEEP_ZSHRC=yes \
        sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
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

    # Avoid associative arrays so this works on macOS system bash 3.2
    install_plugin "$base" zsh-autosuggestions https://github.com/zsh-users/zsh-autosuggestions
    install_plugin "$base" zsh-syntax-highlighting https://github.com/zsh-users/zsh-syntax-highlighting
    install_plugin "$base" zsh-completions https://github.com/zsh-users/zsh-completions
}

sources_omz() {
    grep -q 'oh-my-zsh\.sh' "$1" 2>/dev/null
}

# ZSH_THEME and plugins=() only take effect if they are set *before*
# oh-my-zsh.sh is sourced, so insert above that line when it already exists.
add_config_line() {
    local file="$1" line="$2" tmp
    if sources_omz "$file"; then
        tmp="$(mktemp)"
        awk -v ins="$line" '
            !inserted && /oh-my-zsh\.sh/ { print ins; inserted=1 }
            { print }
        ' "$file" > "$tmp"
        cat "$tmp" > "$file"
        rm -f "$tmp"
    else
        printf '\n%s\n' "$line" >> "$file"
    fi
}

# Oh My Zsh is installed with KEEP_ZSHRC=yes, so a pre-existing ~/.zshrc
# (WSL/Ubuntu creates one) is left untouched and never loads the framework.
# Without this, ZSH_THEME is ignored and `p10k` is never defined.
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
    local desired="plugins=(git zsh-autosuggestions zsh-syntax-highlighting zsh-completions)"

    if grep -q '^plugins=(' "$file" 2>/dev/null; then
        if sed --version >/dev/null 2>&1; then
            sed -i "s/^plugins=(.*)/${desired}/" "$file"
        else
            sed -i.bak "s/^plugins=(.*)/${desired}/" "$file"
            rm -f "${file}.bak"
        fi
    else
        add_config_line "$file" "$desired"
    fi
}

write_managed_block() {
    local file="$1"
    local tmp
    tmp="$(mktemp)"

    # Strip previous managed block if present
    if [[ -f "$file" ]] && grep -qF "$MARKER_BEGIN" "$file"; then
        awk -v b="$MARKER_BEGIN" -v e="$MARKER_END" '
            $0 == b { skip=1; next }
            $0 == e { skip=0; next }
            !skip { print }
        ' "$file" > "$tmp"
        mv "$tmp" "$file"
    fi

    local bat_cmd="bat"
    if ! command -v bat >/dev/null 2>&1 && command -v batcat >/dev/null 2>&1; then
        bat_cmd="batcat"
    fi

    local fd_cmd="fd"
    if ! command -v fd >/dev/null 2>&1 && command -v fdfind >/dev/null 2>&1; then
        fd_cmd="fdfind"
    fi

    cat >> "$file" <<EOF

${MARKER_BEGIN}
# Managed by Pro-Terminal-Setup-For-AI-Devs — safe to re-run the installer.

# History: large, shared, de-duplicated
HISTSIZE=100000
SAVEHIST=100000
setopt HIST_IGNORE_DUPS HIST_IGNORE_SPACE SHARE_HISTORY INC_APPEND_HISTORY EXTENDED_HISTORY

# Faster completion + include zsh-completions
fpath+=("\${ZSH_CUSTOM:-\$HOME/.oh-my-zsh/custom}/plugins/zsh-completions/src")
autoload -Uz compinit && compinit

# Modern CLI aliases
if command -v eza >/dev/null 2>&1; then
  alias ls='eza --group-directories-first --icons=auto'
  alias ll='eza -lah --group-directories-first --git --icons=auto'
  alias la='eza -a --group-directories-first --icons=auto'
  alias lt='eza --tree --level=2 --icons=auto'
else
  alias ll='ls -lah'
  alias la='ls -A'
fi

if command -v ${bat_cmd} >/dev/null 2>&1; then
  alias cat='${bat_cmd} --paging=never'
  alias bat='${bat_cmd}'
  export BAT_THEME='TwoDark'
fi

if command -v ${fd_cmd} >/dev/null 2>&1; then
  alias fd='${fd_cmd}'
fi

command -v rg >/dev/null 2>&1 && alias grep='rg'

# Git shortcuts
alias gs='git status -sb'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline --graph --decorate -20'
alias gd='git diff'
alias gco='git checkout'

# Navigation
alias ..='cd ..'
alias ...='cd ../..'
alias mkdir='mkdir -p'

# fzf keybindings (Ctrl-R history, Ctrl-T files)
if command -v fzf >/dev/null 2>&1; then
  if [[ -f ~/.fzf.zsh ]]; then
    source ~/.fzf.zsh
  elif fzf --zsh >/dev/null 2>&1; then
    source <(fzf --zsh)
  elif [[ -f /usr/share/doc/fzf/examples/key-bindings.zsh ]]; then
    source /usr/share/doc/fzf/examples/key-bindings.zsh
  fi
  export FZF_DEFAULT_COMMAND='${fd_cmd} --type f --hidden --follow --exclude .git'
  export FZF_CTRL_T_COMMAND="\$FZF_DEFAULT_COMMAND"
fi

# Smart directory jumping: z foo
command -v zoxide >/dev/null 2>&1 && eval "\$(zoxide init zsh)"

# Prefer delta for git diffs when available
if command -v delta >/dev/null 2>&1; then
  export GIT_PAGER='delta'
fi

# Editor defaults (override in ~/.zshrc.local)
export EDITOR="\${EDITOR:-vim}"
export VISUAL="\${VISUAL:-\$EDITOR}"

# Machine-local overrides
[[ -f "\$HOME/.zshrc.local" ]] && source "\$HOME/.zshrc.local"
${MARKER_END}
EOF
}

update_zshrc() {
    log "Updating ${ZSHRC}..."
    [[ -f "$ZSHRC" ]] || touch "$ZSHRC"
    backup_file "$ZSHRC"
    ensure_theme "$ZSHRC"
    ensure_plugins_line "$ZSHRC"
    # Must run after theme/plugins so those are set above the source line,
    # and before the managed block so our aliases win over the framework's.
    ensure_omz_bootstrap "$ZSHRC"
    write_managed_block "$ZSHRC"

    if ! sources_omz "$ZSHRC"; then
        warn "$ZSHRC still does not source oh-my-zsh.sh; the theme will not load."
    fi
}

setup_fzf_install_script() {
    # Homebrew fzf ships an optional install script for keybindings
    if [[ "$OS" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
        local fzf_install
        fzf_install="$(brew --prefix)/opt/fzf/install"
        if [[ -x "$fzf_install" && ! -f "$HOME/.fzf.zsh" ]]; then
            log "Configuring fzf key bindings..."
            "$fzf_install" --key-bindings --completion --no-update-rc --no-bash --no-fish >/dev/null || true
        fi
    fi
}

configure_git_delta() {
    if ! command -v delta >/dev/null 2>&1; then
        return
    fi
    if git config --global --get core.pager >/dev/null 2>&1; then
        return
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
    zsh_path="$(command -v zsh)" || return
    if [[ "${SHELL:-}" == "$zsh_path" ]]; then
        log "Default shell already zsh."
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
    cat <<EOF

Setup complete.

Next steps:
  1. Restart your terminal (or run: exec zsh)
  2. Set the terminal font to "MesloLGS Nerd Font" / "MesloLGS NF"
  3. Run: p10k configure   # first-run powerlevel10k wizard

Tips for AI/dev workflows:
  - Use rg / fd / fzf instead of grep / find / history scrolling
  - Use z <dir> (zoxide) to jump to frequent projects
  - Put secrets and machine-only aliases in ~/.zshrc.local
  - Install CLI agents separately (claude, codex, gh) as needed

EOF
}

main() {
    log "Starting professional terminal setup (${OS})..."
    install_packages
    install_oh_my_zsh
    install_powerlevel10k
    install_plugins
    setup_fzf_install_script
    update_zshrc
    configure_git_delta
    set_default_shell
    print_final
}

main "$@"
