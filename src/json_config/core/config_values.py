import dataclasses
import logging
import typing

LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class ConfigValues:
    """Base class for config values.

    Should be subclassed to define specific config fields.

    A field may be tagged with ``metadata={"category": "some_name"}`` to mark
    it as a nested `ConfigValues` that should be represented as a
    nested object (keyed by its category name) rather than a plain attribute.
    This lets several logically-distinct sub-configs be combined into a
    single `ConfigValues` (and persisted through a single
    `~.config_layer.ConfigLayer`) while still being addressable and
    resolvable as their own nested structures.

    Example:
        ```python
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
        MainValues().to_dict()

        # {
        #     "main_window": {"width": 100, "height": 100},
        #     "env": {"name": "test"},
        #     "root_value": 10,
        # }
        ```
    """

    def __post_init__(self) -> None:
        """Run extra initialization after dataclass fields are set."""
        self._validate_fields_categories()

    @classmethod
    def get_fields_names(cls) -> set[str]:
        """Get available config field names.

        Returns:
            set[str]: set of existing field names
        """
        return set(each_field.name for each_field in dataclasses.fields(cls))

    @staticmethod
    def _field_key(field: dataclasses.Field) -> str:
        """Return the key a field should be addressed by.

        This is the field's ``category`` metadata if set, otherwise its own
        attribute name.

        Args:
            field (dataclasses.Field): The dataclass field to resolve a key for.

        Returns:
            str: The resolved key.
        """
        return field.metadata.get("category", field.name)

    @classmethod
    def get_defaults(cls) -> dict[str, typing.Any]:
        """Return a dict of field/category names to their default values.

        Fields whose default value is itself a `ConfigValues`
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

    def _validate_fields_categories(self) -> None:
        """Validate that nested ConfigValues fields declare a category.

        Raises:
            ValueError: If a field's value is itself a `ConfigValues`
                instance but the field was not tagged with
                ``metadata={"category": ...}``.
        """
        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            if isinstance(value, ConfigValues) and "category" not in field.metadata:
                raise ValueError(
                    f"Field '{field.name}' on {type(self).__name__} is a nested "
                    "ConfigValues but is missing metadata={'category': ...}"
                )

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
        Nested `ConfigValues` fields are updated recursively, so
        nested values absent from *data* are left untouched.

        Args:
            data (dict[str, Any]): dictionary of values to update

        Returns:
            ConfigValues: a new instance with updated values
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
