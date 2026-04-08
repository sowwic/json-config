import typing
from graphlib import TopologicalSorter

if typing.TYPE_CHECKING:
    from .config_layer import ConfigLayer


def deep_merge_dicts(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*, returning a new dict.

    - Nested dicts are merged recursively.
    - All other types (including lists) are replaced by the override value.
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def topological_sort_layers(layers: dict[str, ConfigLayer]) -> list[str]:
    """Return layer names in dependency-resolved order (dependencies first).

    Uses :class:`graphlib.TopologicalSorter` from the standard library.

    Raises:
        ValueError: if a dependency is missing or not registered.
        graphlib.CycleError: if a circular dependency is detected.
    """
    for name, layer in layers.items():
        for dep in layer.depends_on:
            if dep not in layers:
                raise ValueError(
                    f"Layer '{name}' depends on '{dep}', which is not registered."
                )

    graph = {name: set(layer.depends_on) for name, layer in layers.items()}
    return list(TopologicalSorter(graph).static_order())
