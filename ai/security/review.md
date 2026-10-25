# Security review — credential store

## Threats

1. **Plaintext secrets** — API keys written to repo JSON, `.env`, shell profiles, or logs.
2. **Remote script install** — curl-pipe installers run unaudited code with user privileges.
3. **Dashboard exposure** — Local UI or reports echoing full tokens to the browser or disk.
4. **Supply-chain package ids** — Unverified npm/pip/winget package names typosquatting agents.
5. **Process argv leakage** — Passing `-w secret` on CLI visible in `ps` on some platforms.
6. **Cross-user secret bleed** — Shared service name without scoping by provider/account.

## Controls implemented (`ai/security/store.py`)

| Control | Mitigation |
|--------|------------|
| OS-backed storage only | macOS Keychain, Windows Credential Manager (set/delete), Linux `secret-tool`. |
| No plaintext fallback | Unsupported OS or missing `secret-tool` returns `ok: false`; never writes JSON/env. |
| Stable key namespace | Service `pro-terminal-setup`, account `{provider}:{name}`. |
| Injectable runner | Tests and callers use a fake runner; production defaults to `subprocess`. |
| Windows get honesty | `get_secret` does not pretend `cmdkey` can read passwords; documents win32 API need. |
| Redaction helper | `redact()` masks token-like strings before logging; secret values never logged. |
| Stdlib-only store | No extra dependencies in the security module surface. |

## Residual risks

- macOS `security -w` still passes the password on argv (OS tool limitation); prefer short-lived tokens.
- Windows retrieval requires future win32 integration for full round-trip from Python.
- Keychain items are only as safe as the user session and backup policy.
- Provider adapters must keep calling `ai.providers.credentials`, not raw files.

## Operator checklist

- Install `libsecret-tools` on Linux before storing keys.
- Do not commit `.env` or local override files with live tokens.
- Treat agent install scripts as untrusted until pinned by hash or package manager.
