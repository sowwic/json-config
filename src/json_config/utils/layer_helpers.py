import typing
from collections.abc import Sequence
from graphlib import TopologicalSorter

if typing.TYPE_CHECKING:
    from ..api import ConfigLayer

_UNSET = object()


def deep_merge_dicts(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*, returning a new dict.

    - Nested dicts are merged recursively.
    - All other types (including lists) are replaced by the override value.

    Args:
        base (dict): The base dictionary to merge into.
        override (dict): The dictionary to merge from.

    Returns:
        dict: The merged dictionary.
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def deep_diff_dicts(current: dict, baseline: dict) -> dict:
    """Recursively compute the subset of *current* that differs from *baseline*.

    For keys present in both dicts as nested dicts, the diff is computed
    recursively so that only the genuinely-diverging leaf values are kept,
    dropping nested keys/sub-keys that match the baseline. All other
    (non-dict, or newly-added) values are kept as-is if they differ from
    (or are absent from) *baseline*.

    This is used to prune a config layer down to only its real overrides,
    including within nested category values.

    Args:
        current: The full, resolved values to diff.
        baseline: The values that would already be inherited without
            *current*'s own contribution.

    Returns:
        dict: A (possibly nested) dict containing only the differing values.
    """
    _unset = object()
    result = {}
    for key, value in current.items():
        base_value = baseline.get(key, _unset)
        if isinstance(value, dict) and isinstance(base_value, dict):
            nested_diff = deep_diff_dicts(value, base_value)
            if nested_diff:
                result[key] = nested_diff
        elif base_value is _unset or base_value != value:
            result[key] = value
    return result


def get_nested(
    data: dict, path: Sequence[str], default: typing.Any = None
) -> typing.Any:
    """Look up a (possibly nested) value in *data* by *path*.

    Args:
        data: The dict to look up the value in.
        path: Sequence of keys addressing the value, e.g. ``("category_a",
            "field_one")`` to look up ``data["category_a"]["field_one"]``.
        default: Value to return if *path* is not fully present in *data*.

    Returns:
        Any: The value found at *path*, or *default*.
    """
    current: typing.Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def pop_nested(data: dict, path: Sequence[str]) -> None:
    """Remove the (possibly nested) value at *path* from *data*, in place.

    Any parent dict that becomes empty as a result of the removal is
    itself removed, so this never leaves behind stale, empty containers.

    Args:
        data: The dict to remove the value from.
        path: Sequence of keys addressing the value to remove.
    """
    if not path:
        return

    key, *rest = path
    if key not in data:
        return

    if not rest:
        del data[key]
        return

    nested = data[key]
    if isinstance(nested, dict):
        pop_nested(nested, rest)
        if not nested:
            del data[key]


def nest_value(path: Sequence[str], value: typing.Any) -> dict:
    """Wrap *value* in nested dicts following *path*.

    Example:
        ```python
        nest_value(("category_a", "field_one"), 42)
        # -> {"category_a": {"field_one": 42}}

    Args:
        path: Sequence of keys to nest the value under.
        value: The value to wrap.

    Returns:
        dict: The nested dict wrapping *value*.
    """
    result = value
    for key in reversed(path):
        result = {key: result}
    return result


def topological_sort_layers(layers: dict[str, ConfigLayer]) -> list[str]:
    """Return layer names in dependency-resolved order (dependencies first).

    Uses `graphlib.TopologicalSorter` from the standard library.

    Args:
        layers (dict[str, ConfigLayer]): The layers to sort.

    Raises:
        ValueError: if a dependency is missing or not registered.
        graphlib.CycleError: if a circular dependency is detected.

    Returns:
        list[str]: The sorted layer names.
    """
    for name, layer in layers.items():
        for dep in layer.depends_on:
            if dep not in layers:
                raise ValueError(
                    f"Layer '{name}' depends on '{dep}', which is not registered."
                )

    graph = {name: set(layer.depends_on) for name, layer in layers.items()}
    return list(TopologicalSorter(graph).static_order())
