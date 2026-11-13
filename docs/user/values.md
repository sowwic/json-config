# Defining values

Settings are fields of a `ConfigValues` subclass. It is a pydantic `BaseModel`,
so types, defaults, validators and `Field` constraints all work. Assignment is
validated (`validate_assignment=True`), and fields can be set by name or by alias
(`populate_by_name=True`).

```python
from json_config.api import ConfigValues, Field


class AppValues(ConfigValues):
    theme: str = "light"
    font_size: int = Field(default=12, ge=6, le=72)
    recent_files: list[str] = Field(default_factory=list)
```

!!! note
    Lists are replaced, not merged. If a layer sets `recent_files`, that list wins
    entirely over the one from lower layers. Only dicts (categories) are merged
    key by key.

## Nested categories

Group related settings with nested `ConfigValues` classes. A nested field **must**
declare an `alias`, which becomes its key in the JSON file. Without one, defining
the class raises `ValueError`.

```python
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

Layers are deep-merged, so a layer can override `window.width` without repeating
`window.height`. Categories nest to any depth.

## Describing fields

Pydantic can read the string under a field as its description. Turn it on in a
shared base class and write the docs next to the settings:

```python
from pydantic import ConfigDict


class BaseValues(ConfigValues):
    model_config = ConfigDict(use_attribute_docstrings=True)


class BridgeValues(BaseValues):
    """Server external processes connect to."""

    enabled: bool = True
    """Start the server when the application launches."""
    port: int | None = Field(default=None, ge=0, le=65535)
    """Port to listen on. None tries the default port and the ones after it."""
```

`model_config` set on a subclass is merged with the one on `ConfigValues`, so
`populate_by_name` and `validate_assignment` stay on.

## Bounds

`get_field_bounds(name)` returns the `(minimum, maximum)` declared with `ge`/`gt`
and `le`/`lt`; a side is `None` when unbounded. Handy for building a settings UI.

```python
AppValues.get_field_bounds("font_size")   # (6, 72)
AppValues.get_field_bounds("theme")       # (None, None)
```

Other class-level helpers:

| Method | Returns |
| --- | --- |
| `get_fields_names()` | Set of field attribute names (not aliases). |
| `get_defaults()` | Nested dict of the defaults, keyed by alias where one is set. |

## Converting to and from dicts

`to_dict()` returns the values as a nested dict keyed by alias, which is what ends
up in the JSON files. `replace(data)` returns a **new** instance updated from such a
dict; keys missing from `data` keep their current value and nested categories are
updated recursively. `LayeredConfig` uses these two for `save()` and `resolve()`.

## Migrating or cleaning data with hooks

Four hooks run around `to_dict` and `replace`. Each runs for every nested category
too, on its own instance.

| Hook | Runs | Use it to |
| --- | --- | --- |
| `pre_serialize(self)` | Start of `to_dict()` (so on `save()`) | Modify the instance in place, e.g. trim a list. |
| `post_serialize(self, data)` | End of `to_dict()` | Change the dict that gets written. Return it. |
| `pre_deserialize(self, data)` | Start of `replace()` (so on `resolve()`) | Clean or migrate incoming data, e.g. rename an old key. Return it. |
| `post_deserialize(self)` | End of `replace()` | Fix up the new instance. Return it. |

```python
import pathlib


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

Renaming a key between releases:

```python
class AppValues(ConfigValues):
    theme: str = "light"

    def pre_deserialize(self, data):
        if "colour_scheme" in data:           # key used by an older version
            data = {**data, "theme": data["colour_scheme"]}
        return data
```
