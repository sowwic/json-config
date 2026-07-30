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

    A field may be tagged with ``metadata={"category": "some_name"}`` to mark
    it as a nested :class:`ConfigValues` that should be represented as a
    nested object (keyed by its category name) rather than a plain attribute.
    This lets several logically-distinct sub-configs be combined into a
    single :class:`ConfigValues` (and persisted through a single
    :class:`~.config_layer.ConfigLayer`) while still being addressable and
    resolvable as their own nested structures.

    Example::

        @dataclasses.dataclass
        class MainWindowValues(ConfigValues):
            width: int = 100
            height: int = 100

        @dataclasses.dataclass
        class EnvValues(ConfigValues):
            name: str = "test"

        @dataclasses.dataclass
        class MainValues(ConfigValues):
            main_window: MainWindowValues = dataclasses.field(
                default_factory=MainWindowValues, metadata={"category": "main_window"}
            )
            env: EnvValues = dataclasses.field(
                default_factory=EnvValues, metadata={"category": "env"}
            )
            root_value: int = 10

        # MainValues().to_dict() ->
        # {
        #     "main_window": {"width": 100, "height": 100},
        #     "env": {"name": "test"},
        #     "root_value": 10,
        # }
    """

    @classmethod
    def get_fields_names(cls) -> set[str]:
        """Get available config field names.

        Returns:
            set: set of existing field names
        """
        return set(each_field.name for each_field in dataclasses.fields(cls))

    @staticmethod
    def _field_key(field: dataclasses.Field) -> str:
        """Return the key a field should be addressed by.

        This is the field's ``category`` metadata if set, otherwise its own
        attribute name.

        Args:
            field: The dataclass field to resolve a key for.

        Returns:
            str: The resolved key.
        """
        return field.metadata.get("category", field.name)

    @classmethod
    def get_defaults(cls) -> dict[str, typing.Any]:
        """Return a dict of field/category names to their default values.

        Fields whose default value is itself a :class:`ConfigValues`
        (typically tagged with ``metadata={"category": ...}``) are expanded
        recursively into nested dicts, keyed by their category name (or
        their own attribute name if no category is set).

        Returns:
            dict[str, Any]: dictionary of keys to their default values
        """
        defaults = {}
        for field in dataclasses.fields(cls):
            if field.default is not dataclasses.MISSING:
                value = field.default
            elif field.default_factory is not dataclasses.MISSING:
                value = field.default_factory()
            else:
                continue

            if isinstance(value, ConfigValues):
                value = value.get_defaults()

            defaults[cls._field_key(field)] = value

        return defaults

    def to_dict(self) -> dict[str, typing.Any]:
        """Convert this instance to a plain (possibly nested) dict.

        Fields tagged with ``metadata={"category": ...}`` are nested under
        their category name instead of their raw attribute name.

        Returns:
            dict[str, Any]: dictionary of keys to their current values
        """
        result = {}
        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            if isinstance(value, ConfigValues):
                value = value.to_dict()
            result[self._field_key(field)] = value
        return result

    def replace(self, data: dict[str, typing.Any]) -> typing.Self:
        """Update config values from a (possibly nested) dictionary.

        Keys are matched against each field's category name (if tagged via
        ``metadata={"category": ...}``) or its attribute name otherwise.
        Nested :class:`ConfigValues` fields are updated recursively, so
        nested values absent from *data* are left untouched.

        Args:
            data (dict[str, Any]): dictionary of values to update
        """
        updates: dict[str, typing.Any] = {}
        for field in dataclasses.fields(self):
            key = self._field_key(field)
            if key not in data:
                continue

            value = data[key]
            current = getattr(self, field.name)
            if isinstance(current, ConfigValues) and isinstance(value, dict):
                value = current.replace(value)
            updates[field.name] = value

        return dataclasses.replace(self, **updates)


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
        """Initialize the config.

        Args:
            config_manager (LayeredConfigManager | None, optional): The config manager
                to use, by default None (a new manager is created).
            layer_filter (str | None, optional): The layer filter to use,
                by default None (the root layer is used).
        """
        self._config_manager: LayeredConfigManager = (
            config_manager if config_manager else LayeredConfigManager()
        )
        self._layer_filter: str | None = layer_filter
        self._values: T = self.VALUES_CLASS()

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

        Returns:
            str | None: The current layer filter, or None if not set.
        """
        return self._layer_filter

    @layer_filter.setter
    def layer_filter(self, layer_name: str | None):
        self._layer_filter = layer_name

    @property
    def values(self) -> T:
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
        """Return the default values for this config.

        Returns:
            ConfigValues: The default values.
        """

        return self.VALUES_CLASS()

    def write_to_layer(self, layer_name: str):
        """Write the current values to the specified layer.

        Parameters
        ----------
        layer_name : str
            The name of the layer to write to.
        """

        layer = self.manager[layer_name]
        update_dict = {
            k: v for k, v in self._values.to_dict().items() if k in layer.get_data()
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
