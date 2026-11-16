# Saving and reverting

## Saving only real overrides

`save()` compares the current values with what the layer's dependencies already
provide and writes only the differences. If you set a value back to what is
inherited, it disappears from the file.

```python
config = AppConfig(layer_filter="user")
config.resolve()

config.values.font_size = 16
config.save()   # user.json -> {"theme": "dark", "font_size": 16}

config.values.font_size = 14   # same as the project layer
config.save()   # user.json -> {"theme": "dark"}
```

The comparison goes down into nested categories, so a category keeps just the fields
that differ:

```python
config.values.window.width = 1024
config.save()   # user.json -> {"window": {"width": 1024}}
```

`write_to_layer(name)` does the diff and stores it on a layer **without** writing the
file, if you want to save later with `config.layer_manager.save(name)`.

## First save

`save()` first seeds every root layer with the defaults from your `ConfigValues` class
(for keys the layer doesn't have yet) and creates its file if it doesn't exist. So the
first `save()` leaves you with a complete `defaults.json` that you can ship or edit,
and the layers above it hold only their overrides. A layer that has no data and no
file is not written.

!!! warning
    Seeding covers **all** root layers, not just the one you save to. Registering a
    root layer with a `file_path` and calling `save()` creates that file.

## Reverting a value

`revert_value()` removes a field's override from the current layer and restores the
inherited value (or the default). Nested values can be addressed with a dotted path.
Call `save()` afterwards to persist the change.

```python
config.revert_value("theme")
config.revert_value("window.width")   # only this leaf, siblings are kept
config.save()
```

Without a dot the name is the attribute name of a top-level field and reverts the
whole field, including every override inside a category. An unknown name raises
`ValueError`. In a dotted path use the keys as they appear in the JSON, i.e. aliases.

## Resetting

`config.reset()` replaces the values with the defaults from `ConfigValues`, ignoring
every layer. `config.defaults()` returns a fresh default instance without touching
`config.values`. `resolve()` brings the layered values back.
