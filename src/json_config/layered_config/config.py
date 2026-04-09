import dataclasses
import logging
from typing import Any, Self, TypeVar

from .config_manager import LayeredConfigManager

LOGGER = logging.getLogger(__name__)
T = TypeVar("T", bound="ConfigValues")


@dataclasses.dataclass
class ConfigValues:
    @classmethod
    def get_fields_names(cls) -> set[str]:
        """Get available config field names.

        Returns:
            set: set of existing field names
        """
        return set(each_field.name for each_field in dataclasses.fields(cls))

    def replace(self, data: dict[str, Any]) -> Self:
        """Update config values from a dictionary.

        Args:
            data (dict[str, Any]): dictionary of values to update
        """
        filtered_dict = {k: v for k, v in data.items() if k in self.get_fields_names()}
        return dataclasses.replace(self, **filtered_dict)


# TODO: Add writing of defaults to root layers if they don't exist
# TODO: Add context manager for writing to a layer 'with layer_edit(layer_name) ...'
class LayeredConfig[T]:
    VALUES_CLASS: type[T] = ConfigValues

    def __init__(
        self, config_manager: LayeredConfigManager, layer_filter: str | None = None
    ):
        self._config_manager: LayeredConfigManager = config_manager
        self._layer_filter: str | None = layer_filter
        self._values: T = self.VALUES_CLASS()

    @property
    def is_valid_filter(self) -> bool:
        return self._layer_filter in self.layers

    @property
    def manager(self) -> LayeredConfigManager:
        return self._config_manager

    @property
    def layers(self) -> list[str]:
        return list(self._config_manager.sorted_names())

    @property
    def layer_filter(self) -> str:
        return self._layer_filter

    @layer_filter.setter
    def layer_filter(self, layer_name: str | None):
        self._layer_filter = layer_name

    @property
    def values(self) -> T:
        return self._values

    @property
    def available_keys(self) -> set[str]:
        return self.VALUES_CLASS.get_fields_names()

    def resolve(self):
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
        layer_name = self.layer_filter if self.is_valid_filter else self.layers[0]
        self.write_to_layer(layer_name)
        self.manager.save(layer_name)
