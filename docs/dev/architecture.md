# Architecture

```text
json_config
├── api/            the public API: re-exports only
├── core/
│   ├── config_values.py   ConfigValues: pydantic model, to_dict / replace, hooks
│   ├── config_layer.py    ConfigLayer: one named layer of raw data, loads/saves a file
│   ├── layer_manager.py   ConfigLayerManager: owns layers, orders, merges, persists
│   └── config.py          LayeredConfig: typed values bound to a manager
├── utils/
│   └── layer_helpers.py   pure dict functions: merge, diff, nested get/pop, topo sort
└── version.py
```

Anything users should import goes through `json_config/api/__init__.py` and its
`__all__`. Add new public names there.

## Data flow

```text
  JSON files ──load──▶ ConfigLayer._data ──merge (manager.resolve)──▶ dict
                                                                       │ ConfigValues.replace
                                                                       ▼
  JSON files ◀─save─── ConfigLayer._data ◀─diff (write_to_layer)─── ConfigValues (typed)
                                                                       ▲ to_dict
```

Layers hold **plain dicts**, never typed values. Typing happens only at the edge,
in `LayeredConfig`: `resolve()` merges raw dicts and calls `values.replace(...)`;
`save()` calls `values.to_dict()`, diffs it against the layers below and stores the
result on the layer. This keeps layers usable without a `ConfigValues` class (the
manager can be driven directly) and means unknown keys in a file survive a load.

## The pieces

### ConfigValues

A pydantic `BaseModel` with `populate_by_name` and `validate_assignment`.

- **Aliases are the JSON keys.** `_field_key` returns the alias if there is one and the
  attribute name otherwise. `to_dict`, `replace`, `get_defaults` and `revert_value` all
  go through it.
- **A nested `ConfigValues` field must have an alias.** `__pydantic_init_subclass__`
  enforces it (the plain `__init_subclass__` runs before `model_fields` is filled in).
- **`replace` returns a new instance** (`model_copy(update=...)`). It recurses into
  nested categories, so keys absent from the data keep their value. `LayeredConfig`
  reassigns `self._values`, which means a reference to the old `values` object goes
  stale after `resolve()`.
- **Hooks** (`pre_/post_serialize`, `pre_/post_deserialize`) are no-ops in the base
  class. Extension points are added as overridable hooks, not as extra constructor
  arguments or flags.

### ConfigLayer

A dataclass: `name`, `depends_on`, `file_path`, and `_data`.

- `load()` skips a missing or empty file with a warning and raises `ValueError` for a
  non-object. It reads the file text twice (once to test for empty), which is harmless
  but is the first thing to fix if load performance matters.
- `save()` creates parent directories, and does nothing when the layer has neither
  data nor a file, so empty layers don't litter the disk.
- `set`, `unset`, `unset_path`, `replace_data` and `get_data` are the only supported
  ways to touch `_data`. `get_data()` returns a **shallow** copy.

### ConfigLayerManager

Owns `name -> ConfigLayer`. It is a **named singleton**: `_ManagerMeta.__call__`
caches one instance per name, and the constructor arguments of later calls are
ignored. `get_layer_manager(name)` is the same as `ConfigLayerManager(name)`.
`ConfigLayerManager.clear()` empties the cache; it exists for tests.

It does not know about `ConfigValues`. `seed_root_layers(defaults)` takes a plain dict
for that reason.

### LayeredConfig

A generic class (PEP 695 syntax, hence Python 3.12+) with two required class
attributes, `VALUES_CLASS` and `NAME`. `__init__` raises `NotImplementedError` without
`NAME` and instantiates `VALUES_CLASS()` for the initial `values`. It holds a
`layer_filter` instead of a layer: the active layer is looked up by name each time, so
changing the filter or registering layers later just works. `current_layer` falls back
to the first root layer when the filter is unset or invalid, while `resolve()` raises
for an invalid, non-`None` filter. That mismatch is deliberate for `save()` and
`revert_value()`, which always need a target.

### layer_helpers

Pure functions on dicts, with no state, so they are the easiest place to add tests.
`UNSET_DICT_VALUE` is a sentinel distinguishing "key missing" from "key is `None`".
