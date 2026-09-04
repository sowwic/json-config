import logging
import typing

from ..utils import layer_helpers
from .config_values import ConfigValues
from .layer_manager import ConfigLayerManager

LOGGER = logging.getLogger(__name__)
ValuesTypeVar = typing.TypeVar("ValuesTypeVar", bound="ConfigValues")


class LayeredConfig[ValuesTypeVar]:
    """Layered configuration class.

    Provides a way to access and update config values from multiple layers.

    Usage::
        class ExampleValues(ConfigValues):
            int_value: int = 0
            str_value: str = ""
            list_value: list[str] = dataclasses.field(
                default_factory=list,
            )

        class ExampleConfig(LayeredConfig[ExampleValues]):
            VALUES_CLASS = ExampleValues
    """

    VALUES_CLASS: type[ValuesTypeVar] = ValuesTypeVar

    def __init__(
        self,
        layer_manager: ConfigLayerManager | None = None,
        layer_filter: str | None = None,
    ):
        """Initialize the config.

        Args:
            layer_manager (ConfigLayerManager | None, optional): The config manager
                to use, by default None (a new manager is created).
            layer_filter (str | None, optional): The layer filter to use,
                by default None (the root layer is used).
        """
        self._layer_manager: ConfigLayerManager = (
            layer_manager if layer_manager else ConfigLayerManager()
        )
        self._layer_filter: str | None = layer_filter
        self._values: ValuesTypeVar = self.VALUES_CLASS()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(layer_filter={self._layer_filter})"

    @property
    def is_valid_filter(self) -> bool:
        """Return whether the layer filter is valid.

        Returns:
            bool: True if the layer filter is valid, False otherwise.
        """
        return self._layer_filter in self.layers

    @property
    def layer_manager(self) -> ConfigLayerManager:
        """
        Return the config layer manager.

        Raises:
            ValueError: If the config layer manager is not set.

        Returns:
            ConfigLayerManager: The config layer manager.
        """
        return self._layer_manager

    @property
    def root_layers(self) -> list[str]:
        """Return the root layers as a dict.

        Returns:
            dict[str, Any]: The root layers.
        """
        return self._layer_manager.root_layers

    @property
    def current_layer(self) -> str | None:
        """Return the current layer filter.

        Returns:
            str: The current layer filter, or the first layer if not set.
        """
        return self._layer_filter if self.is_valid_filter else self.root_layers[0]

    @property
    def layers(self) -> list[str]:
        """Return the list of layer names in topological order.

        Returns:
            list[str]: The list of layer names.
        """

        return list(self._layer_manager.sorted_names())

    @property
    def layer_filter(self) -> str | None:
        """Return the current layer filter.

        Returns:
            str | None: The current layer filter, or None if not set.
        """
        return self._layer_filter

    @layer_filter.setter
    def layer_filter(self, layer_name: str | None):
        self._layer_filter = layer_name

    @property
    def values(self) -> ValuesTypeVar:
        """Return the current values object.

        Returns
        -------
        T: The current values object.
        """
        return self._values

    def resolve(self) -> dict[str, typing.Any]:
        """Resolve the current values from the config manager.

        Returns:
            dict[str, typing.Any]: The resolved values.
        """
        self.layer_manager.load_all()
        sorted_layer_names = self.layer_manager.sorted_names()
        layer_name = sorted_layer_names[0]
        if self.layer_filter in self.layers:
            layer_name = self.layer_filter
        elif self.layer_filter is not None:
            raise ValueError(
                f"Invalid layer filter: {self.layer_filter}, "
                f"valid options are: {self.layers}"
            )

        resolved_dict = self.layer_manager.resolve(up_to=layer_name)
        self._values = self.values.replace(resolved_dict)

        return resolved_dict

    def defaults(self) -> ConfigValues:
        """Return the default values for this config.

        Returns:
            ConfigValues: The default values.
        """

        return self.VALUES_CLASS()

    def write_to_layer(self, layer_name: str):
        """Write the current values to the specified layer.

        Only the fields whose current value differs from what would be
        resolved from *layer_name*'s own dependencies (i.e. without this
        layer's own contribution) are written. This keeps a layer's file
        limited to its own overrides rather than a full copy of inherited
        values, while still allowing the very first write to a brand new,
        previously-empty layer to persist correctly (previously, writes
        were filtered down to keys already present in the layer's data,
        which meant nothing could ever be written to a fresh layer).

        The diff is computed recursively, so nested category values are
        pruned on a per-field basis: if only part of a nested category still
        diverges from the baseline, only that part is kept as an override,
        and fields that now match the baseline (at any depth) are dropped.

        Args:
            layer_name : str
                The name of the layer to write to.
        """

        layer = self.layer_manager[layer_name]
        baseline = self.layer_manager.resolve_many(*layer.depends_on)
        current_dict = self._values.to_dict()
        diff = layer_helpers.deep_diff_dicts(current_dict, baseline)
        layer.replace_data(diff)

    def revert_value(self, field_path: str) -> None:
        """Revert a field's value to what is inherited from the current
        layer's dependencies, discarding any override for it on that layer.

        This immediately removes the field's own override from the current
        layer's raw data, and updates :attr:`values` to reflect the value
        that would be resolved without that layer's own contribution
        (falling back to the field's default if no dependency provides a
        value for it either). Call :meth:`save` afterwards to persist the
        change to disk.

        Args:
            field_path: Either the attribute name of a top-level field
                belonging to this config's ``VALUES_CLASS`` (reverts that
                whole field -- for a nested/category field, this discards
                *all* of its nested overrides), or a dot-separated path
                string addressing a single, possibly nested, leaf field by
                its category/attribute keys, e.g.
                ``"category_a.field_one"``. A nested path only discards the
                override for that one leaf field, leaving sibling overrides
                within the same category untouched -- e.g.::

                    config.revert_value("subcategory.option1")

        Raises:
            ValueError: If *field_path* has no dot and does not name a
                top-level field of this config's ``VALUES_CLASS``.
        """
        if "." in field_path:
            path: tuple[str, ...] = tuple(field_path.split("."))
        else:
            field_name = field_path
            if field_name not in self.VALUES_CLASS.get_fields_names():
                raise ValueError(
                    f"Field '{field_name}' is not a field of "
                    f"{self.VALUES_CLASS.__name__}"
                )
            field_info = self.VALUES_CLASS.model_fields[field_name]
            path = (self.VALUES_CLASS._field_key(field_name, field_info),)

        layer = self.layer_manager[self.current_layer]
        layer.unset_path(path)

        baseline = self.layer_manager.resolve_many(*layer.depends_on)
        defaults = self.VALUES_CLASS.get_defaults()
        _unset = object()
        value = layer_helpers.get_nested(baseline, path, _unset)
        if value is _unset:
            value = layer_helpers.get_nested(defaults, path, _unset)
        if value is not _unset:
            self._values = self._values.replace(layer_helpers.nest_value(path, value))

    def reset(self):
        """Reset the current values to the defaults."""
        self._values = self.VALUES_CLASS()

    def save(self):
        """Save the current values to the active layer."""
        self.layer_manager.seed_root_layers(self.values.get_defaults())
        current_layer = self.current_layer
        self.write_to_layer(current_layer)
        self.layer_manager.save(current_layer)
