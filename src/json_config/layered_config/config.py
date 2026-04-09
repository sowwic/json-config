import dataclasses
import logging
from typing import Any, Self

from .config_manager import ConfigLayer, LayeredConfigManager

LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class ConfigValues:
    pass


class LayeredConfig:
    VALUES_CLASS = ConfigValues

    def __init__(
        self, config_manager: LayeredConfigManager, layer_filter: str | None = None
    ):
        self._config_manager: LayeredConfigManager = config_manager
        self._layer_filter: str | None = layer_filter
        self._values: ConfigValues = self.VALUES_CLASS()

    @property
    def is_valid_filter(self) -> bool:
        return self._layer_filter in self.layers

    @property
    def manager(self) -> LayeredConfigManager:
        return self._config_manager

    @property
    def layers(self) -> list[str]:
        return list(self._config_manager.sorted_names)

    @property
    def layer_filter(self) -> str:
        return self._layer_filter

    @layer_filter.setter
    def layer_filter(self, layer_name: str | None):
        self._layer_filter = layer_name

    @property
    def values(self) -> ConfigValues:
        return self._values

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
        self._values = dataclasses.replace(self.VALUES_CLASS(), **resolved_dict)

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
