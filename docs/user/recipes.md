# Recipes

## An application config class

Most applications want one config class that registers its own layers, so any module
can create it without setup. Register the root layer in `__init__`, and only once:

```python
import pathlib

from json_config.api import ConfigLayer, LayeredConfig

USER_CONFIG_FILE = pathlib.Path("~/.my_app/config.json").expanduser()


class AppConfig(LayeredConfig[AppValues]):
    """The application config.

    Attributes:
        VALUES_CLASS: ConfigValues class to be used with this config
        ROOT_CONFIG_LAYER: Root config layer
    """

    NAME = "general"
    VALUES_CLASS = AppValues
    ROOT_CONFIG_LAYER = ConfigLayer(name="user", file_path=USER_CONFIG_FILE)

    def __init__(self):
        super().__init__(layer_filter=self.ROOT_CONFIG_LAYER.name)
        if self.ROOT_CONFIG_LAYER.name not in self.layer_manager.root_layers:
            self.layer_manager.register(self.ROOT_CONFIG_LAYER)
```

The check against `root_layers` matters: managers are singletons, so a second
`AppConfig()` would otherwise try to register `"user"` again and raise.

Create the config once at startup and share it, instead of calling `resolve()`
everywhere:

```python
_config: AppConfig | None = None


def get_app_config() -> AppConfig:
    """Return the application config, creating and resolving it on first use."""
    global _config
    if _config is None:
        _config = AppConfig()
        _config.resolve()
    return _config
```

## Several independent configs

Each `NAME` gets its own manager, so unrelated parts of an application don't share
layers:

```python
class EditorConfig(LayeredConfig[EditorValues]):
    VALUES_CLASS = EditorValues
    NAME = "editor"


class NetworkConfig(LayeredConfig[NetworkValues]):
    VALUES_CLASS = NetworkValues
    NAME = "network"
```

## Shipping defaults with the application

Keep a read-only `defaults.json` next to the code, and a user file in the user's data
directory (for example from [platformdirs](https://pypi.org/project/platformdirs/)):

```python
manager = get_layer_manager("my_app")
manager.register(ConfigLayer("defaults", file_path=PACKAGE_DIR / "defaults.json"))
manager.register(ConfigLayer("user", depends_on=["defaults"], file_path=USER_FILE))
```

Work on `"user"`; saving never rewrites more than the user's own overrides, apart from
seeding a missing `defaults.json`.

## Testing

A manager and its layers outlive a single test. Drop them between tests, and point
layer files at a temporary directory:

```python
import pytest

from json_config.api import ConfigLayer, ConfigLayerManager


@pytest.fixture
def config(tmp_path):
    ConfigLayerManager.clear()
    manager = ConfigLayerManager("test")
    manager.register(ConfigLayer("user", file_path=tmp_path / "user.json"))
    yield AppConfig(layer_manager=manager, layer_filter="user")
    ConfigLayerManager.clear()
```

`AppConfig(layer_manager=...)` skips the lookup by `NAME`, but the class still needs a
`NAME`. If your config class registers layers in `__init__` (see above), the
`root_layers` check keeps it from registering twice on the manager you pass.
