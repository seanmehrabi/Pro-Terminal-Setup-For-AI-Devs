# Pro Terminal Setup for AI Devs

Cross-platform bootstrap scripts that install a modern shell stack and wire up **idempotent** config for everyday coding and AI-assisted workflows (search, navigation, git, and a clean prompt).

| Platform | Script | Shell / prompt |
|----------|--------|----------------|
| macOS, Debian/Ubuntu (incl. WSL) | [`setup_pro_bash.sh`](setup_pro_bash.sh) | zsh + [Oh My Zsh](https://ohmyz.sh/) + [powerlevel10k](https://github.com/romkatv/powerlevel10k) |
| Windows | [`setup_pro_powershell.ps1`](setup_pro_powershell.ps1) | PowerShell 7 + [Oh My Posh](https://ohmyposh.dev/) (`paradox` theme) |

Both scripts are **safe to re-run**: they back up your profile, replace only a managed block between markers, and skip software that is already installed.

---

## What you get

### CLI tools

| Tool | Purpose |
|------|---------|
| [ripgrep](https://github.com/BurntSushi/ripgrep) (`rg`) | Fast search |
| [fd](https://github.com/sharkdp/fd) | Fast file find |
| [fzf](https://github.com/junegunn/fzf) | Fuzzy finder (history / files) |
| [zoxide](https://github.com/ajeetdsouza/zoxide) (`z`) | Smart directory jumping |
| [eza](https://github.com/eza-community/eza) | Modern `ls` |
| [bat](https://github.com/sharkdp/bat) | Syntax-highlighted `cat` |
| [delta](https://github.com/dandavison/delta) | Better git diffs |
| [jq](https://jqlang.github.io/jq/) | JSON processing |
| [GitHub CLI](https://cli.github.com/) (`gh`) | PRs, issues, auth from the terminal |
| git, curl, wget, tmux, vim, htop | Baseline utilities (bash script) |

On Debian/Ubuntu, missing packages are skipped with a warning (older releases may not ship `eza`, `zoxide`, etc.). Binary names like `batcat` / `fdfind` are aliased where needed.

### Shell experience

**macOS / Linux**

- Oh My Zsh + powerlevel10k
- Plugins: `git`, `zsh-autosuggestions`, `zsh-syntax-highlighting`, `zsh-completions`
- Large shared history, fzf keybindings, zoxide, git aliases (`gs`, `ga`, `gc`, …)
- Optional git **delta** pager (only if `core.pager` is not already set)
- Default shell switched to zsh when possible

**Windows**

- Oh My Posh + PSReadLine (predictions) + Terminal-Icons
- Git helpers as **functions** so built-in aliases (`gc`, `gp`, `gl`) are not clobbered
- eza / bat / zoxide / `rg` wired when present

### Font

**MesloLGS Nerd Font** (glyphs for powerline / icons):

- **macOS:** Homebrew cask `font-meslo-lg-nerd-font`
- **Windows:** Oh My Posh font install, or direct download of Nerd Fonts Meslo
- **Linux / WSL:** install a Nerd Font on the host and set it in the terminal (e.g. Windows Terminal for WSL)

---

## Requirements

| OS | Prerequisites |
|----|----------------|
| **macOS** | [Homebrew](https://brew.sh) |
| **Debian / Ubuntu / WSL** | `sudo` for `apt-get`; internet access |
| **Windows** | [winget](https://learn.microsoft.com/windows/package-manager/winget/) (App Installer from the Microsoft Store). Admin is **not** required for CurrentUser installs. |

Clone the repo (preferred over piping scripts from the network), then run the script for your platform.

```bash
git clone https://github.com/<you>/Pro-Terminal-Setup-For-AI-Devs.git
cd Pro-Terminal-Setup-For-AI-Devs
```

---

## macOS & Ubuntu (WSL)

```bash
bash setup_pro_bash.sh
```

### After setup

1. Restart the terminal, or run `exec zsh`
2. Set the terminal font to **MesloLGS Nerd Font** / **MesloLGS NF**
3. Run `p10k configure` for the first-time powerlevel10k wizard

### What the script changes

- Installs packages via Homebrew or apt
- Installs Oh My Zsh, powerlevel10k, and zsh plugins (if missing)
- Backs up `~/.zshrc` to `~/.zshrc.bak.<timestamp>`
- Sets `ZSH_THEME` and `plugins=(…)`, above the `source $ZSH/oh-my-zsh.sh` line
- Adds the Oh My Zsh bootstrap (`export ZSH=…` + `source …/oh-my-zsh.sh`) when
  your existing `~/.zshrc` doesn't already load it
- Appends/refreshes a managed block between:

  ```text
  # >>> pro-terminal-setup >>>
  ...
  # <<< pro-terminal-setup <<<
  ```

- May run `chsh` to make zsh the default shell
- Configures git delta globals only when no `core.pager` is set

---

## Windows (PowerShell 7+)

From PowerShell (Windows Terminal recommended):

```powershell
# If needed: allow this session to run local scripts
Set-ExecutionPolicy -Scope Process Bypass

.\setup_pro_powershell.ps1
```

Optional switches:

```powershell
.\setup_pro_powershell.ps1 -SkipTools   # Oh My Posh + profile only
.\setup_pro_powershell.ps1 -SkipFont    # skip Nerd Font install
```

If you are still on Windows PowerShell 5.x, the script installs **PowerShell 7** via winget and exits—re-run from `pwsh.exe` to finish.

### After setup

1. Restart Windows Terminal / PowerShell
2. Set the font to **MesloLGS Nerd Font** (or MesloLGS NF)
3. Optional: `oh-my-posh config export --output ~\.mytheme.omp.json` and point the profile at your theme

### What the script changes

- Installs Oh My Posh, PSReadLine, Terminal-Icons
- Installs dev tools via winget (unless `-SkipTools`)
- Installs Meslo Nerd Font for the current user (unless `-SkipFont`)
- Backs up `$PROFILE` to `$PROFILE.bak.<timestamp>`
- Writes/refreshes the same style of managed marker block in your PowerShell 7 profile

---

## Customizing (safe zone)

**Do not put secrets or machine-only settings inside the managed marker block**—re-running the installer will replace that section.

| Platform | Local override file (not overwritten) |
|----------|----------------------------------------|
| macOS / Linux | `~/.zshrc.local` (sourced at end of the managed block) |
| Windows | `%USERPROFILE%\Documents\PowerShell\Microsoft.PowerShell_profile.local.ps1` |

Examples for `~/.zshrc.local`:

```bash
export EDITOR=nvim
# export ANTHROPIC_API_KEY=...   # keep API keys out of git and out of managed blocks
alias projects='cd ~/projects'
```

Themes and plugins:

- **zsh / p10k:** edit `ZSH_THEME`, `plugins=(…)`, or run `p10k configure`; see the [Oh My Zsh wiki](https://github.com/ohmyzsh/ohmyzsh/wiki)
- **Oh My Posh:** change the `oh-my-posh init` line in the managed block (or move theme choice into your local profile after init); see [Oh My Posh docs](https://ohmyposh.dev/docs)

---

## Tips for AI / dev workflows

- Prefer **`rg` / `fd` / `fzf`** over slow `grep` / `find` / scrolling history
- Use **`z <partial-dir>`** (zoxide) to jump between projects
- Use **`gh`** for clone, PR, and auth flows agents and humans share
- Install agent CLIs yourself when you need them (Claude Code, Codex, Cursor, etc.)—this repo focuses on the shell substrate they run in
- Keep tokens and host-specific paths in the **local** override files above

---

## Troubleshooting

**`zsh: command not found: p10k`** (and a plain `hostname%` prompt instead of a themed one)

`p10k` is a function that powerlevel10k defines when Oh My Zsh loads it, so this
means your `~/.zshrc` never sourced the framework. Oh My Zsh is installed with
`KEEP_ZSHRC=yes`, so a `~/.zshrc` that already existed — Ubuntu and WSL create a
basic one — is left untouched and never loads it. The script now adds the
bootstrap itself; re-run it and open a new shell:

```bash
bash setup_pro_bash.sh && exec zsh
```

To check by hand, `~/.zshrc` should contain a line sourcing `oh-my-zsh.sh`, with
`ZSH_THEME` and `plugins=(…)` set *above* it.

**`line 3: set: pipefail: invalid option name`** (often shown garbled, e.g. `: invalid option namene 3: set: pipefail`)

The script was copied or checked out with Windows CRLF line endings, so bash reads
`pipefail\r` instead of `pipefail` — and the stray carriage return scrambles the
error message itself. The script now detects this and re-runs a corrected copy,
but you can also fix the file in place:

```bash
sed -i 's/\r$//' setup_pro_bash.sh
```

To prevent it entirely, clone with the repo's `.gitattributes` in place (it pins
`*.sh` to LF), or re-check-out an existing clone:

```bash
git rm --cached -r . && git reset --hard
```

**`bad interpreter: /usr/bin/env bash^M`** is the same problem hitting the shebang
when the script is run as `./setup_pro_bash.sh`. Apply the `sed` fix above, or run
it as `bash setup_pro_bash.sh` and let the self-heal handle it.

---

## Safety & re-runs

| Behavior | Detail |
|----------|--------|
| Backups | Every profile write creates `*.bak.<yyyyMMdd-HHmmss>` |
| Idempotent tools | Existing packages, OMZ, plugins, fonts, modules are skipped when detected |
| Managed block | Content between the `pro-terminal-setup` markers is replaced on each run |
| Outside the block | Your other `.zshrc` / `$PROFILE` content is left alone (theme/plugins lines on zsh are updated in place) |

To undo the managed config: restore a backup, or delete the marker block from your profile. Installed packages and Oh My Zsh are not removed automatically.

---

## License

[MIT](LICENSE) © Sean Mehrabi
