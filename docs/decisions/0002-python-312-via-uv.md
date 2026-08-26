# ADR 0002 — Python 3.12 via a uv-managed standalone build

Status: accepted (M0.1)
Date: 2026-08-26

## Context

SPEC §3 pins Python 3.12. On this machine (macOS 26 / Darwin 25.2), Homebrew's
`python@3.12` and `python@3.14` bottles fail at `import pyexpat`:

```
Symbol not found: _XML_SetAllocTrackerActivationThreshold
Expected in: /usr/lib/libexpat.1.dylib
```

The bottles were built against a newer libexpat than the OS ships. `venv`
creation itself fails as a result. Building from source is blocked by outdated
Command Line Tools, whose fix needs `sudo` and a system update. Homebrew
`python@3.11` works, but deviates from the pin.

## Decision

Install **uv** (Homebrew, single static binary) and use it to manage a
**standalone CPython 3.12** (`uv python install 3.12` →
`cpython-3.12.14`, bundles its own libexpat 2.8.3). The repo pins the version
in `.python-version` and `requires-python = ">=3.12,<3.13"`; `uv sync` builds
`.venv/` and `uv.lock`.

## Alternatives rejected

- **Homebrew `python@3.11`.** Works today, but breaks the SPEC pin for a
  reason unrelated to the project.
- **Fix Xcode CLT + rebuild `python@3.12` from source.** Needs a user-driven
  `sudo rm -rf /Library/Developer/CommandLineTools` and a system update.
  Out of scope for an automated milestone; can revisit.
- **Wait for a corrected Homebrew bottle.** Unbounded.
- **pyenv.** Also builds from source → same CLT blocker.

## Consequences

- `uv` becomes the project's env/dependency manager. It brings no
  infrastructure (no daemon, no services) — comparable to pandoc as a CLI. Not
  in the SPEC §3 stack list; recorded here and in `dependencies.md`.
- All commands run as `uv run …`. CI and the future M1 Docker image should pin
  the same 3.12 so the interpreter is identical everywhere.
- Revisit if/when Homebrew ships a working `python@3.12` for this OS — switching
  back is a one-line change.
