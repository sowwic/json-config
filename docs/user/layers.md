# Layers

A layer is a named dict of overrides, optionally loaded from and saved to a JSON
file. Layers form a graph through `depends_on`: a layer overrides the layers it
depends on.

```python
from json_config.api import ConfigLayer, get_layer_manager

manager = get_layer_manager("my_app")
manager.register(ConfigLayer("defaults", file_path=defaults_path))
manager.register(ConfigLayer("project", depends_on=["defaults"], file_path=project_path))
manager.register(ConfigLayer("user", depends_on=["project"], file_path=user_path))
```

```text
config/defaults.json   {"theme": "light", "font_size": 12}
config/project.json    {"font_size": 14}
~/.my_app/user.json    {"theme": "dark"}
```

```python
config = AppConfig(layer_filter="user")
config.resolve()
config.values.theme       # "dark"  (user)
config.values.font_size   # 14      (project)
```

- A layer with an empty `depends_on` is a **root** layer.
- Registering the same name twice raises `ValueError`.
- A dependency that isn't registered raises `ValueError` when resolving, and a
  circular dependency raises `graphlib.CycleError`.
- `depends_on` takes several names. Layers are merged dependencies first; when two
  independent branches set the same key, the order between them is not defined, so
  keep overlapping branches to different keys.
- `manager.unregister(name)` removes a layer. References to it from other layers are
  your problem.

## Which layer is active

`layer_filter` picks the layer a `LayeredConfig` works on. `resolve()` merges that
layer and everything beneath it, and `save()` writes to it. With no filter,
only the first layer in dependency order (a root layer) is used, so name the layer you
want to see the layers above it.

```python
config = AppConfig(layer_filter="project")
config.resolve()
config.values.theme       # "light"  (the user layer is ignored)

config.layer_filter = None  # back to the root layer
```

An unknown `layer_filter` makes `resolve()` raise `ValueError` listing the valid
names. `config.layers` lists the layer names in dependency order, and
`config.root_layers` the roots.

This is what a settings dialog with a "scope" selector needs: one `AppConfig` per
scope, or one that you re-point and re-resolve.

## Loading layers from a directory tree

`register_from_paths_tree` builds a chain of layers from a nested dict. Each key is a
JSON file path, the layer name is the file stem, and nesting defines `depends_on`:

```python
manager.register_from_paths_tree(
    {
        "config/defaults.json": {
            "config/team.json": {
                "config/user.json": {},
            },
        },
    }
)
# defaults  (no parent)
# team      (depends_on=["defaults"])
# user      (depends_on=["team"])
```

Siblings under one key all depend on that key, so a tree can branch. Because the name
is the file stem, two files with the same stem in different folders clash.

## Using the manager directly

`LayeredConfig` covers most needs. The manager is available as `config.layer_manager`
for the rest:

| Method | Does |
| --- | --- |
| `load_all()` | Load every layer from its file. |
| `resolve(up_to=None)` | Merged dict, up to and including a layer. |
| `resolve_many(*names)` | Merge several branches, later names winning. |
| `save(name)` / `save_all()` | Write one layer, or every layer that has a file. |
| `manager["user"]` | The `ConfigLayer`; `.set(key=value)` and `.get_data()` edit and read its raw data. |

```python
manager["user"].set(theme="dark")
manager.save("user")
```
