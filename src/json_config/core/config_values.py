import logging
import typing

from pydantic import BaseModel, ConfigDict

LOGGER = logging.getLogger(__name__)


class ConfigValues(BaseModel):
    """Base class for config values.

    Should be subclassed to define specific config fields.

    A field may be given `Field(alias="some_name")` to mark it as a nested
    `ConfigValues` that should be represented as a nested object (keyed by
    its alias) rather than a plain attribute. This lets several
    logically-distinct sub-configs be combined into a single `ConfigValues`
    while still being addressable and resolvable as their own nested
    structures.

    Example:
        ```python
        class MainWindowValues(ConfigValues):
            width: int = 100
            height: int = 100

        class EnvValues(ConfigValues):
            name: str = "test"

        class MainValues(ConfigValues):
            main_window: MainWindowValues = Field(
                default_factory=MainWindowValues, alias="main_window"
            )
            env: EnvValues = Field(default_factory=EnvValues, alias="env")
            root_value: int = 10

        MainValues().to_dict()

        # {
        #     "main_window": {"width": 100, "height": 100},
        #     "env": {"name": "test"},
        #     "root_value": 10,
        # }
        ```
    """

    model_config = ConfigDict(populate_by_name=True, validate_assignment=True)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: typing.Any) -> None:
        """Validate that nested ConfigValues fields declare an alias.

        Uses pydantic's own subclass hook (rather than the plain
        `__init_subclass__`) because `model_fields` is only fully populated
        by the time this hook runs.
        """
        super().__pydantic_init_subclass__(**kwargs)
        cls._validate_fields_categories()

    @classmethod
    def get_fields_names(cls) -> set[str]:
        """Get available config field names.

        Returns:
            set[str]: set of existing field names (attribute names, not
                aliases).
        """
        return set(cls.model_fields.keys())

    @staticmethod
    def _field_key(name: str, field: typing.Any) -> str:
        """Return the key a field should be addressed by.

        This is the field's alias if set, otherwise its own attribute name.

        Args:
            name: The field's attribute name.
            field: The pydantic `FieldInfo` for that field.

        Returns:
            str: The resolved key.
        """
        return field.alias if field.alias is not None else name

    @classmethod
    def get_defaults(cls) -> dict[str, typing.Any]:
        """Return a dict of field/category names to their default values.

        Fields whose default value is itself a `ConfigValues` (typically
        given an alias) are expanded recursively into nested dicts, keyed by
        their alias (or their own attribute name if no alias is set).

        Returns:
            dict[str, Any]: dictionary of keys to their default values
        """
        defaults = {}
        for name, field in cls.model_fields.items():
            if field.default_factory is not None:
                value = field.default_factory()
            elif field.default is not None:
                value = field.default
            else:
                continue

            if isinstance(value, ConfigValues):
                value = value.get_defaults()

            defaults[cls._field_key(name, field)] = value

        return defaults

    @classmethod
    def _validate_fields_categories(cls) -> None:
        """Validate that nested ConfigValues fields declare an alias.

        Raises:
            ValueError: If a field's annotated type is itself a
                `ConfigValues` subclass but the field was not given an
                alias.
        """
        for name, field in cls.model_fields.items():
            annotation = field.annotation
            if isinstance(annotation, type) and issubclass(annotation, ConfigValues):
                if field.alias is None:
                    raise ValueError(
                        f"Field '{name}' on {cls.__name__} is a nested "
                        "ConfigValues but is missing Field(alias=...)"
                    )

    def to_dict(self) -> dict[str, typing.Any]:
        """Convert this instance to a plain (possibly nested) dict.

        Fields with an alias set are nested under their alias name instead
        of their raw attribute name.

        Returns:
            dict[str, Any]: dictionary of keys to their current values
        """
        result = {}
        for name, field in type(self).model_fields.items():
            value = getattr(self, name)
            if isinstance(value, ConfigValues):
                value = value.to_dict()
            result[self._field_key(name, field)] = value
        return result

    def replace(self, data: dict[str, typing.Any]) -> typing.Self:
        """Update config values from a (possibly nested) dictionary.

        Keys are matched against each field's alias (if set) or its
        attribute name otherwise. Nested `ConfigValues` fields are updated
        recursively, so nested values absent from *data* are left untouched.

        Args:
            data (dict[str, Any]): dictionary of values to update

        Returns:
            ConfigValues: a new instance with updated values
        """
        updates: dict[str, typing.Any] = {}
        for name, field in type(self).model_fields.items():
            key = self._field_key(name, field)
            if key not in data:
                continue

            value = data[key]
            current = getattr(self, name)
            if isinstance(current, ConfigValues) and isinstance(value, dict):
                value = current.replace(value)
            updates[name] = value

        return self.model_copy(update=updates)
