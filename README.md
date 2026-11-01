# Json Config

![Tests](https://github.com/sowwic/json-config/actions/workflows/unit_tests.yml/badge.svg)
![Code Quality](https://github.com/sowwic/json-config/actions/workflows/code_quality.yml/badge.svg)

Layered JSON configuration with typed values. Define your settings as a
[pydantic](https://docs.pydantic.dev) model, stack any number of JSON files on
top of each other (defaults → workspace → user, ...), and read the merged
result as a typed object. Edits are written back to a single layer, and only
the values that actually differ from the layers below it are saved.

## Installation

```bash
pip install git+https://github.com/sowwic/json-config.git
```

Requires Python 3.12+.

## Core concepts

| Concept | What it does |
| --- | --- |
| `ConfigValues` | Pydantic model describing your settings and their defaults. |
| `ConfigLayer` | One named layer, optionally backed by a JSON file. `depends_on` lists the layers it overrides. |
| `ConfigLayerManager` | Owns the layers and deep-merges them in dependency order. Managers are named singletons. |
| `LayeredConfig` | The object you use in your app. Binds a `ConfigValues` class to a manager and exposes `resolve()`, `save()` and `revert_value()`. |

## Quick start

```python
import pathlib

from json_config.api import (
    ConfigLayer,
    ConfigValues,
    LayeredConfig,
    get_layer_manager,
)


class AppValues(ConfigValues):
    theme: str = "light"
    font_size: int = 12
    recent_files: list[str] = []


class AppConfig(LayeredConfig[AppValues]):
    VALUES_CLASS = AppValues
    NAME = "my_app"  # required: selects the layer manager


# Register layers once at startup. Order of registration doesn't matter,
# `depends_on` decides which layer overrides which.
manager = get_layer_manager("my_app")
manager.register(ConfigLayer("defaults", file_path=pathlib.Path("config/defaults.json")))
manager.register(
    ConfigLayer(
        "user",
        depends_on=["defaults"],
        file_path=pathlib.Path("~/.my_app/user.json").expanduser(),
    )
)

config = AppConfig(layer_filter="user")  # work on the "user" layer
config.resolve()                          # load files and merge the layers
print(config.values.theme)                # "light" unless a layer overrides it

config.values.theme = "dark"
config.save()                             # writes only {"theme": "dark"} to user.json
```

`NAME` is mandatory on every `LayeredConfig` subclass. `AppConfig()` looks the
manager up by that name (creating it if it doesn't exist yet), so every config
class that shares a `NAME` shares the same layers.

## Use cases

### Defaults, workspace and user overrides

Ship a `defaults.json`, let a project override it, and let each user override
that. Higher layers only contain what they change:

```
config/defaults.json   {"theme": "light", "font_size": 12}
config/project.json    {"font_size": 14}
~/.my_app/user.json    {"theme": "dark"}
```

```python
manager = get_layer_manager("my_app")
manager.register(ConfigLayer("defaults", file_path=defaults_path))
manager.register(ConfigLayer("project", depends_on=["defaults"], file_path=project_path))
manager.register(ConfigLayer("user", depends_on=["project"], file_path=user_path))

config = AppConfig()
config.resolve()
config.values.theme       # "dark"  (user)
config.values.font_size   # 14      (project)
```

### Previewing what a lower layer provides

`layer_filter` limits resolution to a layer and the layers beneath it, which is
useful for settings dialogs with a "scope" selector:

```python
config = AppConfig(layer_filter="project")
config.resolve()
config.values.theme       # "light"  (user layer is ignored)

config.layer_filter = None  # back to the root layer
```

Use `config.layers` to list the available layer names in dependency order.

### Saving only real overrides

`save()` compares the current values with what the layer's dependencies
already provide and writes only the differences. If you set a value back to
what is inherited, it disappears from the file.

```python
config = AppConfig(layer_filter="user")
config.resolve()

config.values.font_size = 16
config.save()   # user.json -> {"theme": "dark", "font_size": 16}

config.values.font_size = 14   # same as the project layer
config.save()   # user.json -> {"theme": "dark"}
```

On first save, root layers whose files don't exist yet are created and seeded
with the defaults from your `ConfigValues` class.

### Reverting a value

`revert_value()` removes a field's override from the current layer and
restores the inherited value (or the default). Nested values can be addressed
with a dotted path. Call `save()` afterwards to persist the change.

```python
config.revert_value("theme")
config.revert_value("window.width")   # only this leaf, siblings are kept
config.save()
```

### Nested categories

Group related settings with nested `ConfigValues` classes. A nested field
must declare an `alias`, which becomes its key in the JSON file:

```python
from pydantic import Field


class WindowValues(ConfigValues):
    width: int = 800
    height: int = 600


class AppValues(ConfigValues):
    theme: str = "light"
    window: WindowValues = Field(default_factory=WindowValues, alias="window")
```

```json
{
    "theme": "dark",
    "window": {"width": 1024}
}
```

Layers are deep-merged, so a layer can override `window.width` without
repeating `window.height`.

### Loading layers from a directory tree

`register_from_paths_tree` builds a chain of layers from a nested dict. Each
key is a JSON file path, the layer name is the file stem, and nesting defines
`depends_on`:

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

### Several independent configs

Each `NAME` gets its own manager, so unrelated parts of an application don't
share layers:

```python
class EditorConfig(LayeredConfig[EditorValues]):
    VALUES_CLASS = EditorValues
    NAME = "editor"


class NetworkConfig(LayeredConfig[NetworkValues]):
    VALUES_CLASS = NetworkValues
    NAME = "network"
```

You can also pass a manager explicitly, e.g. in tests:
`AppConfig(layer_manager=my_manager)` (the class still needs a `NAME`).
Call `ConfigLayerManager.clear()` to drop all managers between tests.

### Migrating or cleaning data with hooks

`ConfigValues` has hooks that run when values are serialised (`to_dict`, used
by `save()`) and deserialised (`replace`, used by `resolve()`):

```python
class RecentValues(ConfigValues):
    recent_files: list[str] = []

    def pre_deserialize(self, data):
        # drop files that no longer exist when loading
        files = data.get("recent_files", [])
        return {**data, "recent_files": [f for f in files if pathlib.Path(f).exists()]}

    def pre_serialize(self):
        # keep only the 10 most recent entries when saving
        self.recent_files = self.recent_files[:10]
```

Available hooks: `pre_serialize`, `post_serialize`, `pre_deserialize`,
`post_deserialize`.

## Development

```bash
uv sync
uv run pytest
```
