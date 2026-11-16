# Testing

```bash
make pytest                                          # everything, with coverage
uv run pytest tests/core/test_config.py::test_name   # one test
make pytest-pdb                                      # verbose, pdb on failure
```

Coverage (`--cov=json_config --cov-report=term-missing`) is always on through
`addopts`. Tests mirror the source tree: `tests/core/test_<module>.py` for each module
in `src/json_config/core/`.

## Fixtures

- JSON files live in `tests/fixtures/` (`config_testing/` for configs and layer
  chains, `layer_testing/` for malformed layer files).
- Tests that write files use `.test_output/` in the working directory, which
  `make clean` and `make pytest-pdb` remove. Copy a fixture there before saving; never
  save into `tests/fixtures/`.
- `tests/conftest.py` holds the shared `ConfigValues` classes, layer chains and the
  fixtures that create them.

## Singleton reset

Managers are cached per name for the whole process, so state leaks between tests. Call
`ConfigLayerManager.clear()` before and after any test that creates a manager (the
shared fixtures already do). A test failing only when run after another is almost
always this.

## What to cover

- **Layer helpers**: new behavior in `deep_merge_dicts`, `deep_diff_dicts` and the
  nested helpers gets a direct unit test with plain dicts.
- **Round trips**: change a value, `save()`, build a new config, `resolve()`, compare.
  This catches mismatches between `to_dict`, the diff and `replace`.
- **Nested categories**: test a field at the top level and inside a category, with and
  without a sibling override.
- **Hooks**: a hook that changes data on `save()` or `resolve()` needs both directions
  tested.
- **Errors**: invalid `layer_filter`, missing `NAME`, duplicate layer names, missing
  dependencies, non-object JSON files.
