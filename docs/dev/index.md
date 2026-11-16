# Developer Guide

This guide is for people who work on json-config itself.

## Setup

```bash
uv sync
make check        # ruff + pytest
make mkdocs       # serve these docs
```

`make help` lists every target. Ruff uses a line length of 89 and the `E`, `F` and
`UP` rules. Docstrings are Google style, because the API reference is generated from
them (`mkdocs-autoapi` + `mkdocstrings`), so every public class and method needs one.

## Pages

| Page | What you learn |
| --- | --- |
| [Architecture](architecture.md) | The modules, who calls whom, and the design decisions behind them. |
| [Resolution and saving](resolution.md) | How layers are ordered and merged, and how `save()` and `revert_value()` decide what to write. |
| [Testing](testing.md) | Fixtures, the singleton reset, and what to cover. |
| [Releasing](releasing.md) | Branches, versions, the changelog and `make release`. |
| API reference | Generated from the docstrings (see the navigation). |
