#!/usr/bin/env bash
set -e

OS="$(uname)"

install_packages() {
    if [[ "$OS" == "Darwin" ]]; then
        if ! command -v brew >/dev/null 2>&1; then
            echo "Homebrew not found. Please install Homebrew first: https://brew.sh" >&2
            exit 1
        fi
        brew update
        brew install zsh git curl wget tmux fzf bat exa vim htop
    elif [[ -f /etc/debian_version ]]; then
        sudo apt update
        sudo apt install -y zsh git curl wget tmux fzf bat exa vim htop
    else
        echo "Unsupported OS" >&2
        exit 1
    fi
}

install_oh_my_zsh() {
    if [ ! -d "$HOME/.oh-my-zsh" ]; then
        sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
    fi
}

install_powerlevel10k() {
    local dest="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k"
    if [ ! -d "$dest" ]; then
        git clone --depth=1 https://github.com/romkatv/powerlevel10k.git "$dest"
    fi
}

install_plugins() {
    local base="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins"
    if [ ! -d "$base/zsh-autosuggestions" ]; then
        git clone https://github.com/zsh-users/zsh-autosuggestions "$base/zsh-autosuggestions"
    fi
    if [ ! -d "$base/zsh-syntax-highlighting" ]; then
        git clone https://github.com/zsh-users/zsh-syntax-highlighting "$base/zsh-syntax-highlighting"
    fi
}

update_zshrc() {
    local file="$HOME/.zshrc"
    [ -f "$file" ] || touch "$file"

    grep -q "ZSH_THEME=\"powerlevel10k/powerlevel10k\"" "$file" || \
        sed -i.bak "s/^ZSH_THEME=.*/ZSH_THEME=\"powerlevel10k\/powerlevel10k\"/" "$file" || \
        echo "ZSH_THEME=\"powerlevel10k/powerlevel10k\"" >> "$file"

    if grep -q "plugins=(" "$file"; then
        sed -i.bak 's/plugins=(\([^)]*\))/plugins=(\1 zsh-autosuggestions zsh-syntax-highlighting)/' "$file"
    else
        echo "plugins=(git zsh-autosuggestions zsh-syntax-highlighting)" >> "$file"
    fi

    grep -q "alias ll='ls -la'" "$file" || echo "alias ll='ls -la'" >> "$file"
    grep -q "alias gs='git status'" "$file" || echo "alias gs='git status'" >> "$file"
}

set_default_shell() {
    if [ "$SHELL" != "$(which zsh)" ]; then
        chsh -s "$(which zsh)"
    fi
}

print_final() {
    echo -e "\nSetup complete! Restart the terminal."
    if [[ "$OS" == "Darwin" ]]; then
        echo "If you do not have the MesloLGS NF font, install it via Homebrew:"
        echo "  brew tap homebrew/cask-fonts && brew install font-meslo-lg-nerd-font"
    else
        echo "Install a Nerd Font like MesloLGS NF and set it in your terminal."
    fi
}

install_packages
install_oh_my_zsh
install_powerlevel10k
install_plugins
update_zshrc
set_default_shell
print_final
