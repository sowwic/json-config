# User Guide

This guide is for people who use json-config in an application.

## Installation

```bash
pip install git+https://github.com/sowwic/json-config.git
```

Requires Python 3.12+. The only runtime dependency is pydantic.

## Pages

| Page | What you learn |
| --- | --- |
| [Getting started](getting-started.md) | The four building blocks and a complete first example. |
| [Defining values](values.md) | Typed settings, nested categories, bounds, descriptions and migration hooks. |
| [Layers](layers.md) | Registering layers, how they override each other, previewing a layer, directory trees. |
| [Saving and reverting](saving.md) | What `save()` writes, `revert_value()`, resetting. |
| [Recipes](recipes.md) | An application config class, several independent configs, testing. |
