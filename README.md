# Pro Terminal Setup for AI Devs

One command, one **identical** pro-grade zsh experience on macOS and Ubuntu/WSL: the
powerlevel10k **rainbow prompt ships preconfigured** (no wizard), Tab opens a fuzzy
picker for completions ([fzf-tab](https://github.com/Aloxaf/fzf-tab)), your history
ghost-types ahead of you (autosuggestions), commands colorize as you type (syntax
highlighting), and a curated modern CLI toolbox replaces the 1970s defaults.

## Quick start

**macOS**

```bash
git clone https://github.com/seanmehrabi/Pro-Terminal-Setup-For-AI-Devs.git && cd Pro-Terminal-Setup-For-AI-Devs && bash setup_pro_bash.sh && exec zsh
```

**Ubuntu / WSL** (`--brew` gets the same current tool versions as macOS)

```bash
git clone https://github.com/seanmehrabi/Pro-Terminal-Setup-For-AI-Devs.git && cd Pro-Terminal-Setup-For-AI-Devs && bash setup_pro_bash.sh --brew && exec zsh
```

That's it — the rainbow prompt appears immediately (set the font to **MesloLGS NF** for the icons; on WSL the script already downloaded the fonts to your Windows `Downloads\MesloLGS-NF`).

The script takes care of itself:

- **Existing setup detected?** It asks: **[U]pdate in place** (default, safe), **[R]einstall fresh** (old install backed up first, never deleted), or **[Q]uit**. Non-interactive runs default to update; force with `--update` / `--reinstall`.
- **Something failed?** Every step is checkpointed. The error tells you the step, the cause, and the log file — fix it and re-run the same command; finished steps are skipped and it resumes exactly where it broke.
- **Permissions handled up front:** it refuses to run under `sudo` (that would configure root's shell), verifies sudo/network/dotfile ownership *before* changing anything, and prints the exact fix when a check fails.
- **Everything is backed up:** `~/.zshrc` before every change, the whole old install on reinstall. Log + progress live in `~/.cache/pro-terminal-setup/`.

| Platform | Script | Shell / prompt |
|----------|--------|----------------|
| macOS, Debian/Ubuntu (incl. WSL) | [`setup_pro_bash.sh`](setup_pro_bash.sh) | zsh + [Oh My Zsh](https://ohmyz.sh/) + [powerlevel10k](https://github.com/romkatv/powerlevel10k) rainbow preset |
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

On Linux, **Homebrew is used whenever available** (and `--brew` installs it), so you get the
same current tool versions as macOS. With plain apt, missing packages are skipped with a
warning and `batcat` / `fdfind` naming is handled automatically at shell startup.

### Shell experience

**macOS / Linux — identical on both**

- Oh My Zsh + powerlevel10k with the repo's **rainbow preset** ([`config/p10k.zsh`](config/p10k.zsh))
  installed to `~/.p10k.zsh` — the prompt looks right on first launch, no wizard.
  Instant prompt is enabled, so new shells feel instant.
- **`Tab`** — [fzf-tab](https://github.com/Aloxaf/fzf-tab): every completion (flags, paths,
  git branches, `cd` targets with a live directory preview) opens in a fuzzy picker
- **`→`** — [zsh-autosuggestions](https://github.com/zsh-users/zsh-autosuggestions): accepts
  the gray inline suggestion drawn from your history and completions
- **`Ctrl-R` / `Ctrl-T`** — fzf fuzzy history search / file picker
- [zsh-syntax-highlighting](https://github.com/zsh-users/zsh-syntax-highlighting) +
  extra completions from [zsh-completions](https://github.com/zsh-users/zsh-completions)
- 100k shared, de-duplicated history; case-insensitive completion matching
- `z <dir>` jumping (zoxide), eza/bat aliases, git shortcuts (`gs`, `ga`, `gc`, …)
- git **delta** pager (only if `core.pager` is not already set); on WSL,
  `core.autocrlf=input` (only if unset) so Windows line endings never bite again
- Default shell switched to zsh when possible

**Windows**

- Oh My Posh + PSReadLine (predictions) + Terminal-Icons
- Git helpers as **functions** so built-in aliases (`gc`, `gp`, `gl`) are not clobbered
- eza / bat / zoxide / `rg` wired when present

### Font

**MesloLGS NF** (the font powerlevel10k is designed for):

- **macOS:** installed via Homebrew cask `font-meslo-lg-nerd-font`
- **WSL:** the script downloads all 4 `MesloLGS NF` files to your **Windows** `Downloads\MesloLGS-NF`
  folder — select them, right-click → **Install**, then set Windows Terminal's font to `MesloLGS NF`
- **Windows:** Oh My Posh font install, or direct download of Nerd Fonts Meslo

---

## Requirements

| OS | Prerequisites |
|----|----------------|
| **macOS** | [Homebrew](https://brew.sh) |
| **Debian / Ubuntu / WSL** | a user with `sudo` rights and internet access — the script verifies both up front and prints the fix if either is missing |
| **Windows** | [winget](https://learn.microsoft.com/windows/package-manager/winget/) (App Installer from the Microsoft Store). Admin is **not** required for CurrentUser installs. |

Run the script as **your normal user, not with `sudo`** — it refuses `sudo` (that would set up
root's shell) and asks for your password itself only where apt needs it. Clone the repo
(preferred over piping scripts from the network), then use the [Quick start](#quick-start)
command for your platform.

---

## macOS & Ubuntu (WSL)

```bash
bash setup_pro_bash.sh
```

### Options

| Flag | What it does |
|------|--------------|
| `--brew` | Linux: install/use Homebrew for the toolbox — same current tool versions as macOS. **Recommended on WSL**; plain apt skips whatever your Ubuntu release lacks (often `eza`, a modern `fzf`) with a warning. Auto-used if brew is already installed. |
| `--reinstall` | Back up the existing Oh My Zsh install, plugins and prompt preset to `~/.pro-terminal-setup-backup-<timestamp>/`, then install everything clean. Nothing is ever deleted. |
| `--update` | Refresh an existing install in place without asking (what re-runs do by default when non-interactive). |
| `--insecure-ssl` | **Last resort** for TLS-broken environments: disables certificate verification for this run's downloads. Try a plain run first — the script auto-repairs the CA store and, on WSL, imports the Windows certificate store, which properly fixes corporate SSL inspection. |
| `-h`, `--help` | Usage, including recovery notes. |

### If something goes wrong

The script is built to recover, not to be babysat:

1. **Preflight checks first** — sudo access, network to GitHub, and dotfile ownership are
   verified *before* anything is modified. Each failure prints the exact command that fixes it
   (e.g. the `chown` for a root-owned `~/.zshrc`, the `apt-get install sudo` for a bare container).
2. **Checkpointed steps** — the 9 install steps (`packages`, `oh-my-zsh`, `powerlevel10k`,
   `plugins`, `prompt-preset`, `fonts`, `zshrc`, `git-config`, `default-shell`) are recorded in
   `~/.cache/pro-terminal-setup/completed-steps` as they finish. A successful run clears the file.
3. **On failure** you get the step name, line, exit code, and the log path
   (`~/.cache/pro-terminal-setup/setup.log` — every run appends to it). Fix the cause, re-run the
   same command, and it **resumes at the failed step**; everything already done is skipped.
4. **Escape hatches** — `rm ~/.cache/pro-terminal-setup/completed-steps` re-runs all steps
   (harmless: each one is idempotent); `--reinstall` starts from a clean slate with the old
   install preserved in a backup folder.

Running it with `sudo` is refused by design — that would configure root's shell instead of yours.
The script asks for your sudo password itself, only for `apt`.

### After setup

1. Start a fresh shell: `exec zsh` — the rainbow prompt appears immediately
2. Set the terminal font to **MesloLGS NF**
   (WSL: install the 4 fonts from `Downloads\MesloLGS-NF` first — see [Font](#font))
3. Optional: `p10k configure` any time you want a different prompt style

### What the script changes

- Installs packages via Homebrew and/or apt (`--brew` bootstraps Linuxbrew)
- Installs Oh My Zsh, powerlevel10k, and the 4 zsh plugins (if missing)
- Copies the prompt preset to `~/.p10k.zsh` (**never** overwrites an existing one)
- Backs up `~/.zshrc` to `~/.zshrc.bak.<timestamp>` before every change
- Sets `ZSH_THEME`, `plugins=(…)` and the zsh-completions `fpath`, all above the
  `source $ZSH/oh-my-zsh.sh` line (added if your `~/.zshrc` doesn't load Oh My Zsh)
- Writes two managed blocks it fully owns:

  ```text
  # >>> pro-terminal-setup:top >>>     ← brew PATH + p10k instant prompt (top of file)
  # >>> pro-terminal-setup >>>         ← history, completion, aliases, fzf, zoxide (end of file)
  ```

- May run `chsh` to make zsh the default shell
- git: delta pager only when no `core.pager` is set; WSL `core.autocrlf=input` only when unset

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

## Daily drivers (zsh)

| Keys | What happens |
|------|--------------|
| `Tab` | Fuzzy picker for any completion — flags, paths, branches; `cd` shows a live preview |
| `→` | Accept the gray autosuggestion from your history |
| `Ctrl-R` | Fuzzy-search your entire shell history |
| `Ctrl-T` | Fuzzy-pick a file path into the current command |
| `z <dir>` | Jump to any directory you've visited before |
| `ll` / `lt` | Rich listing / tree via eza, with git status and icons |

## Tips for AI / dev workflows

- Prefer **`rg` / `fd` / `fzf`** over slow `grep` / `find` / scrolling history
- Use **`gh`** for clone, PR, and auth flows agents and humans share
- Install agent CLIs yourself when you need them (Claude Code, Codex, Cursor, etc.)—this repo focuses on the shell substrate they run in
- Keep tokens and host-specific paths in the **local** override files above

---

## Troubleshooting

**`curl: (60) SSL certificate problem: unable to get local issuer certificate`**

Very common on corporate WSL machines: an SSL-inspecting proxy (Zscaler, Netskope, …)
re-signs all HTTPS traffic with a company root CA that Windows trusts but your fresh
Ubuntu doesn't. The script now fixes this itself, in order:

1. Reinstalls/refreshes `ca-certificates` (apt works over plain http, so this succeeds
   even while TLS is broken)
2. On WSL, exports every trusted root certificate from the **Windows** certificate store
   via PowerShell and adds them to Ubuntu's trust store (`update-ca-certificates`) — after
   this, curl, git, brew and everything else trust the corporate proxy permanently

Just re-run the script; if both repairs fail it prints the remaining options (get the CA
file from IT, fix WSL clock drift with `sudo hwclock -s`, or — on a network you trust —
`--insecure-ssl` as a last resort).

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

**Boxes / question marks instead of icons** — the terminal font isn't MesloLGS NF yet.
On WSL the fonts are waiting in Windows `Downloads\MesloLGS-NF`; install them and set
the font in Windows Terminal → Settings → your Ubuntu profile → Appearance → Font face.

---

## Safety & re-runs

| Behavior | Detail |
|----------|--------|
| Backups | Every profile write creates `*.bak.<yyyyMMdd-HHmmss>`; a full reinstall moves the old install to `~/.pro-terminal-setup-backup-<timestamp>/` instead of deleting it |
| Resume | Failed runs keep their checkpoints; re-running skips completed steps and continues from the failure |
| Existing installs | Detected on start — you choose update-in-place (default) or a clean reinstall |
| Idempotent tools | Existing packages, OMZ, plugins, fonts, modules are skipped when detected |
| Managed blocks | Only content between the `pro-terminal-setup` markers is replaced on each run |
| Outside the blocks | Your other `.zshrc` / `$PROFILE` content is left alone (theme/plugins lines on zsh are updated in place) |
| Logs | Every run appends to `~/.cache/pro-terminal-setup/setup.log` |

To undo the managed config: restore a backup, or delete the marker blocks from your profile. Installed packages and Oh My Zsh are not removed automatically.

---

## License

[MIT](LICENSE) © Sean Mehrabi
