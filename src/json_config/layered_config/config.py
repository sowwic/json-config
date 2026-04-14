import dataclasses
import logging
import typing

from .config_manager import LayeredConfigManager

LOGGER = logging.getLogger(__name__)
T = typing.TypeVar("T", bound="ConfigValues")


@dataclasses.dataclass
class ConfigValues:
    """Base class for config values.

    Should be subclassed to define specific config fields.
    """

    @classmethod
    def get_fields_names(cls) -> set[str]:
        """Get available config field names.

        Returns:
            set: set of existing field names
        """
        return set(each_field.name for each_field in dataclasses.fields(cls))

    @classmethod
    def get_defaults(cls) -> dict[str, typing.Any]:
        """Return a dict of field names to their default values.

        Returns:
            dict[str, Any]: dictionary of field names to their default values
        """
        defaults = {}
        for field in dataclasses.fields(cls):
            if field.default is not dataclasses.MISSING:
                defaults[field.name] = field.default
            elif field.default_factory is not dataclasses.MISSING:
                defaults[field.name] = field.default_factory()

        return defaults

    def replace(self, data: dict[str, typing.Any]) -> typing.Self:
        """Update config values from a dictionary.

        Args:
            data (dict[str, Any]): dictionary of values to update
        """
        filtered_dict = {k: v for k, v in data.items() if k in self.get_fields_names()}
        return dataclasses.replace(self, **filtered_dict)


class LayeredConfig[T]:
    """Layered configuration class.

    Provides a way to access and update config values from multiple layers.

    Usage::
        @dataclasses.dataclass
        class ExampleValues(ConfigValues):
            int_value: int = 0
            str_value: str = ""
            list_value: list[str] = dataclasses.field(
                default_factory=list,
            )

        class ExampleConfig(LayeredConfig[ExampleValues]):
            VALUES_CLASS = ExampleValues
    """

    VALUES_CLASS: type[T] = ConfigValues

    def __init__(
        self,
        config_manager: LayeredConfigManager | None = None,
        layer_filter: str | None = None,
    ):
        self._config_manager: LayeredConfigManager = (
            config_manager if config_manager else LayeredConfigManager()
        )
        self._layer_filter: str | None = layer_filter
        self._values: T = self.VALUES_CLASS()

    @property
    def is_valid_filter(self) -> bool:
        """Return whether the layer filter is valid.

        Returns:
            bool: True if the layer filter is valid, False otherwise.
        """
        return self._layer_filter in self.layers

    @property
    def manager(self) -> LayeredConfigManager:
        """
        Return the config manager.

        Raises:
            ValueError: If the config manager is not set.

        Returns:
            LayeredConfigManager: The config manager.
        """
        return self._config_manager

    @property
    def root_layers(self) -> list[str]:
        """Return the root layers as a dict.

        Returns:
            dict[str, Any]: The root layers.
        """
        return self._config_manager.root_layers

    @property
    def current_layer(self) -> str:
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

        return list(self._config_manager.sorted_names())

    @property
    def layer_filter(self) -> str | None:
        """Return the current layer filter.

        Returns
        -------
        str | None: The current layer filter, or None if not set.
        """
        return self._layer_filter

    @layer_filter.setter
    def layer_filter(self, layer_name: str | None):
        self._layer_filter = layer_name

    @property
    def values(self) -> T:
        """Return the current values object."""
        return self._values

    def resolve(self) -> dict[str, typing.Any]:
        """Resolve the current values from the config manager."""
        self.manager.load_all()
        sorted_layer_names = self.manager.sorted_names()
        layer_name = sorted_layer_names[0]
        if self.layer_filter in self.layers:
            layer_name = self.layer_filter
        elif self.layer_filter is not None:
            raise ValueError(
                f"Invalid layer filter: {self.layer_filter}, "
                f"valid options are: {self.layers}"
            )

        resolved_dict = self.manager.resolve(up_to=layer_name)
        self._values = self.values.replace(resolved_dict)

        return resolved_dict

    def defaults(self) -> ConfigValues:
        """Return the default values for this config."""
        return self.VALUES_CLASS()

    def write_to_layer(self, layer_name: str):
        """Write the current values to the specified layer."""
        layer = self.manager[layer_name]
        update_dict = {
            k: v
            for k, v in dataclasses.asdict(self._values).items()
            if k in layer.get_data()
        }
        layer.set(**update_dict)

    def reset(self):
        """Reset the current values to the defaults."""
        self._values = self.VALUES_CLASS()

    def save(self):
        """Save the current values to the active layer."""
        self.manager.seed_root_layers(self.values.get_defaults())
        current_layer = self.current_layer
        self.write_to_layer(current_layer)
        self.manager.save(current_layer)
