# Getting started

## Core concepts

| Concept | What it does |
| --- | --- |
| `ConfigValues` | Pydantic model describing your settings and their defaults. |
| `ConfigLayer` | One named layer, optionally backed by a JSON file. `depends_on` lists the layers it overrides. |
| `ConfigLayerManager` | Owns the layers and deep-merges them in dependency order. Managers are named singletons. |
| `LayeredConfig` | The object you use in your app. Binds a `ConfigValues` class to a manager and exposes `resolve()`, `save()` and `revert_value()`. |

Everything is importable from `json_config.api`.

## A first example

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


# Register layers once at startup. The order of registration doesn't matter,
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

What happened:

1. `AppConfig` is bound to the manager called `"my_app"`. Every config class that
   shares a `NAME` shares the same layers.
2. `resolve()` loads every layer file, deep-merges the layers from the bottom up to
   the `layer_filter` layer and puts the result into `config.values`. Keys no
   layer provides keep the defaults of `AppValues`.
3. `values` is a typed pydantic object. Assigning to it is validated.
4. `save()` writes the difference between the values and the layers below `user`
   into `user.json`.

`NAME` is mandatory. Without it `AppConfig()` raises `NotImplementedError`, unless
you pass a manager yourself (`AppConfig(layer_manager=manager)`), and even then the
class has to define `NAME`.

## Files

A layer file is a JSON object with only the keys that layer sets. Missing files
and empty files are skipped with a warning, so a layer can start out without a
file on disk. A file that holds anything other than an object raises `ValueError`
when loaded.

```json
{
    "theme": "dark"
}
```
