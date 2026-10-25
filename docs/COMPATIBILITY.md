# Compatibility verification

This document records what was actually exercised on each platform. Until a row is updated with dated test evidence, treat native install verification on that OS as **pending until tests recorded**.

| Platform | Native install verified | Automated tests (CI/local) | Notes |
| -------- | ----------------------- | ---------------------------- | ----- |
| macOS    | pending until tests recorded | partial (see below)        | Local QA run on darwin host |
| Windows  | pending until tests recorded | pending until tests recorded | PowerShell parse + adapter unit tests only when CI runs |
| Linux    | pending until tests recorded | pending until tests recorded | Adapter unit tests when CI runs on ubuntu-latest |

## Contract checks (shared)

These behaviors are covered by `tests/shared/test_catalog.py` and `tests/shared/test_engine.py`:

- `python3 -m ai list` exits 0 and lists profiles `coding`, `chat`, `agents`, `local`.
- Catalog load merges base YAML and platform source overlays.
- `build_plan` marks applications as `skip` when the platform adapter `detect` reports installed.
- `dry-run` completes without requiring network access (socket/urlopen blocked in tests; CLI dry-run for `--profile local`).

## macOS — local run (2026-10-25)

Environment: developer machine (`darwin`), Python 3 system `python3`, repo branch `feature/universal-ai-workstation`.

| Command | Result |
| ------- | ------ |
| `python3 -m ai list` | **pass** (exit 0) |
| `python3 -m ai dry-run --profile coding` | **pass** (exit 0; local detect only) |
| `PYTHONPATH=. python3 -m unittest discover -s tests/shared -p "test_*.py" -v` (plus `tests/linux`, `tests/macos`, `tests/windows`) | **pass** — 60 + 10 + 6 + 4 tests (2026-10-25) |
| `bash -n setup_ai.sh` | **pass** |
| `bash -n setup_pro_bash.sh` | **pass** |
| `shellcheck setup_ai.sh` | **pass** (no findings) |
| `shellcheck setup_pro_bash.sh` | **info** only (SC2086, SC2016 ×3); not mass-rewritten per repo policy |

No vendor AI applications were installed during verification.

## Windows

Native Windows install paths were **not** verified on a Windows host in this QA pass. GitHub Actions is configured to parse-check `setup_ai.ps1` on `windows-latest`. Full `setup_ai.ps1` / winget flows remain **pending until tests recorded** on Windows.

## Linux

Native Linux package installs were **not** verified on a Linux host in this QA pass. Ubuntu CI runs Python unit tests and ShellCheck on `setup_ai.sh`. Distro-specific adapter behavior is partially covered by `tests/linux/` when executed on Linux runners.

## GitHub Actions workflow

Workflow file: `.github/workflows/ai-workstation.yml` (name: **AI Workstation**).

- Triggers: `pull_request`, push to `main` and `feature/universal-ai-workstation`.
- Matrix: `macos-latest`, `windows-latest`, `ubuntu-latest`.
- Does **not** install AI applications.
- `dry-run` in CI is **not** a substitute for a real install test.

## Dashboard

`dashboard/package.json` exists; there is no `package-lock.json` at time of writing. CI uses `npm install` and the dashboard job is `continue-on-error: true` until a lockfile is committed.
