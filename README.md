# Professional Terminal Setup

A cross-platform guide to quickly bootstrap a productive shell environment for Windows, macOS and Linux. These scripts install Oh My Posh or Oh My Zsh with helpful plugins and the Meslo Nerd Font so your terminal looks and works great. :rocket:

## Windows PowerShell 7+

Run the PowerShell setup script as administrator:

```powershell
./setup_pro_powershell.ps1
```

The script installs **PowerShell 7**, [Oh My Posh](https://ohmyposh.dev/), `PSReadLine`, and `Terminal-Icons`. It also downloads the **MesloLGS NF** font and updates your `$PROFILE` to load the `paradox` theme with handy aliases.
After running, restart PowerShell and change the terminal font to *MesloLGS NF*.

## Ubuntu (WSL) or macOS

Execute the bash script:

```bash
bash setup_pro_bash.sh
```

It installs required packages such as `zsh`, `tmux`, `fzf`, and more using **apt** on Ubuntu or **Homebrew** on macOS. The script sets up [Oh My Zsh](https://ohmyz.sh/), the `powerlevel10k` theme, and plugins for autosuggestions and syntax highlighting. Aliases like `ll` and `gs` are added to your `.zshrc` and `zsh` becomes the default shell.

On macOS you'll be prompted to install the MesloLGS NF font via Homebrew. Linux users should download a Nerd Font and configure their terminal to use it.

## Customizing

Both Oh My Posh and Oh My Zsh offer many themes. Edit your `$PROFILE` or `.zshrc` to switch themes or add plugins. For more configuration examples, see the [official documentation](https://ohmyposh.dev/docs) and [Oh My Zsh wiki](https://github.com/ohmyzsh/ohmyzsh/wiki).

Enjoy your new terminal! :tada:
