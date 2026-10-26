# AI workstation installer architecture

The pro terminal setup scripts (`setup_pro_bash.sh`, `setup_pro_powershell.ps1`) are unchanged in scope: they configure the shell, CLI toolbox, and prompt. **AI tooling is optional** and lives behind a separate entrypoint so you can adopt it when you want.

## Entry points

| Platform | Terminal setup (unchanged) | Optional AI installer |
|----------|----------------------------|------------------------|
| macOS / Linux / WSL | `bash setup_pro_bash.sh` | `bash setup_ai.sh` |
| Windows | `.\setup_pro_powershell.ps1` | `.\setup_ai.ps1` (owned separately; not run automatically) |

From the repo root you can also run the Python module directly:

```bash
python3 -m ai list
python3 -m ai check
python3 -m ai dry-run --profile coding
python3 -m ai install --yes --profile coding
```

Logs append to `~/.cache/pro-terminal-setup/ai-setup.log`. Non-secret provider settings may later use `~/.config/pro-terminal-setup/ai-config.json` (no secrets in repo tooling).

## Catalog

- `ai/catalog/applications.yaml` — canonical app records (`id`, `name`, `cost`, `auth`, `summary`, `official_url`, `profiles`, per-OS `platforms`).
- `ai/catalog/profiles.yaml` — named bundles (`coding`, `chat`, `agents`, `local`) mapping to application ids.
- Optional overlays in `ai/catalog/sources/{macos,windows,linux}.yaml` merge platform-specific install metadata into each app’s `platforms.<os>` block when those files exist.

Loading and merge logic live in `ai/core/catalog.py` using the stdlib YAML subset parser in `ai/core/yaml_lite.py`.

## Host detection

`ai/core/platform.py` exposes `detect_host()` for OS, architecture, distro (Linux), memory, free disk, home directory, and whether `brew` / `winget` are on `PATH`. Adapters and the engine use this dict; nothing is hardcoded to a specific machine model.

## Adapters

Platform install backends implement a shared protocol documented in `ai/adapters/base.py`:

- `detect`, `install`, `update`, `uninstall`, `repair`

`get_adapter(host)` imports `ai.adapters.macos`, `windows`, or `linux` when present. If a module is missing, a stub adapter returns `unsupported` results so the CLI and planner stay usable on every OS.

## Planning engine

`ai/core/engine.py`:

1. **`select_ids`** — resolves app ids from `--profile`, `--all`, and positional ids.
2. **`build_plan`** — for each id, chooses `install`, `skip`, `manual`, `fallback`, or `unsupported` using catalog verification flags, pending methods, adapter detection, and fallback metadata.
3. **`run_plan`** — executes the plan through the adapter; honors `dry_run` (no real installs) and does not call install for `skip`.

## CLI

`python3 -m ai` implements `help`, `list`, `check`, `status`, `dry-run`, `install`, `update`, `repair`, `uninstall`, and `recommend-models` (optional `ai.models` package). Human check output is formatted in `ai/diagnostics/check.py`; `status` emits JSON for automation.

## Security notes

- Do not store API keys or tokens in the catalog or installer logs.
- Keep secrets in your shell local override files or OS keychain; provider wiring belongs in `ai/providers` when added.
