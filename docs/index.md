# Json Config

Layered JSON configuration with typed values. Describe your settings as a
[pydantic](https://docs.pydantic.dev) model, stack any number of JSON files on
top of each other (defaults → workspace → user, ...) and read the merged result
as a typed object. Edits are written back to a single layer, and only the values
that differ from the layers below it are saved.

```python
config = AppConfig(layer_filter="user")
config.resolve()                 # load the files and merge the layers
config.values.theme = "dark"
config.save()                    # user.json -> {"theme": "dark"}
```

| If you want to... | Read |
| --- | --- |
| Use json-config in an application | [User Guide](user/index.md) |
| Work on json-config itself | [Developer Guide](dev/index.md) |
| Look up a class or method | API reference (see the navigation) |
