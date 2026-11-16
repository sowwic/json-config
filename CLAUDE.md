# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Uses `uv`; the Makefile wraps everything (`make help` lists targets).

- `make check` — lint + tests
- `make pytest` — `uv run pytest tests` (coverage is on by default via `addopts`)
- Single test: `uv run pytest tests/core/test_config.py::test_name -k <expr>`
- `make pytest-pdb` — verbose, drops into pdb on failure
- `make lint` / `make lint-fix` / `make format` — Ruff on `src tests` (line length 89, rules E/F/UP; note `lint` targets end in `|| true`, so they never fail the shell)
- `make mkdocs` — serve docs (`docs/`, `mkdocs.yml`)
- `make release VERSION=x.y.z` — runs the shared release script from `sowwic/gh-workflows` (tags `main`, back-merges to `develop`)

Requires Python 3.12+ (code uses PEP 695 generics, e.g. `class LayeredConfig[ValuesTypeVar]`). Only runtime dependency is `pydantic>=2`.

## Architecture

Layered JSON configuration with pydantic-typed values. Public API is re-exported from `src/json_config/api/__init__.py` — new public names must be added there.

Four collaborating classes in `src/json_config/core/`:

- `ConfigValues` (`config_values.py`) — pydantic model users subclass to declare settings/defaults. Provides `to_dict`/`replace` and the `pre_/post_` (de)serialize hooks used for migration and cleanup. Nested categories are nested `ConfigValues` fields that must declare an `alias` (the JSON key).
- `ConfigLayer` (`config_layer.py`) — one named layer, optionally backed by a JSON file; `depends_on` names the layers it overrides.
- `ConfigLayerManager` (`layer_manager.py`) — owns layers and deep-merges them in `depends_on` order (registration order is irrelevant). It is a **named singleton** via the `_ManagerMeta` metaclass: `get_layer_manager(name)` / `ConfigLayerManager(name)` return the same instance per name. Tests must call `ConfigLayerManager.clear()` (see `tests/conftest.py`) to avoid cross-test leakage.
- `LayeredConfig[V]` (`config.py`) — what apps use. Subclasses must set `VALUES_CLASS` and `NAME` (selects the manager; `NotImplementedError` if missing). `layer_filter` restricts resolution to a layer and those beneath it; `resolve()` loads+merges, `save()` writes back to the filtered layer, `revert_value()` removes an override (dotted paths for nested).

Key behavior: `save()` writes only values that differ from what the layer's dependencies already provide (diff computed with helpers in `utils/layer_helpers.py`); on first save, missing root-layer files are created and seeded with defaults from the `ConfigValues` class.

`src/json_config/version.py` has PyInstaller-aware base-dir logic; the package version lives in `pyproject.toml`/`VERSION` and `CHANGELOG.rst`, which should be updated together on release.

Tests mirror `src/` under `tests/core/`, with JSON fixtures in `tests/fixtures/`.

## Conventions

- Google-style docstrings (`Args:`, `Returns:`, `Raises:`).
- Prefer flexibility: when a subclass needs to run code at a point inside a base class's sequence (before or after a step), add an overridable hook (`pre_*` / `post_*`, a no-op in the base class) rather than changing constructor arguments, reordering the subclass `__init__` around `super().__init__`, or copying the base sequence.
- `develop` is the default and PR branch; `main` is the release branch. Record user-visible changes in `CHANGELOG.rst`.

## Development

- If the current branch is `develop`, ask the user for the GitHub issue number before starting work. Use the related branch.
- Do not commit unless asked to.
- Do not update CHANGELOG unless asked to.
- Do not push extra created worktrees to remote. Once work in them is done, patch it back into the feature branch and delete the extra worktree.
- When a task done in a worktree is finished, do this without being asked: exit the worktree (`ExitWorktree` keep), cherry-pick its commit(s) onto the feature branch in the main checkout, then remove the worktree and its branch. Git can't reach the main checkout from inside the worktree session.

## Token hygiene

- Find symbols with the LSP tool if possible before grepping; then Read with offset/limit.
