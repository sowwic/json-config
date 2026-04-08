import dataclasses
import json
import logging
import pathlib
from typing import ClassVar, Self

LOGGER = logging.getLogger(__name__)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

    @classmethod
    def clear_instances(cls):
        """Clear all instances of the class."""
        cls._instances.clear()


@dataclasses.dataclass
class Config(metaclass=Singleton):
    FILE_PATH: ClassVar[pathlib.Path]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name, value in cls.__dict__.items():
            if isinstance(value, (list, dict, set)):
                setattr(
                    cls,
                    name,
                    dataclasses.field(default_factory=lambda v=value: type(v)(v)),
                )
        dataclasses.dataclass(cls)

    @classmethod
    def get_fields_names(cls) -> set[str]:
        """Get available config field names.

        Returns:
            set: set of existing field names
        """
        return set(each_field.name for each_field in dataclasses.fields(cls))

    @classmethod
    def _load_from_json(cls):
        """Create Config instance from given json file.

        Returns:
            Config: new instance
        """
        json_data = json.loads(cls.FILE_PATH.read_text())
        field_names = cls.get_fields_names()
        for json_field_name in list(json_data.keys()):
            if json_field_name not in field_names:
                json_data.pop(json_field_name)
                LOGGER.warning(f"Unused config field name: {json_field_name}")

        LOGGER.info(f"Loaded config: {cls.FILE_PATH}")

        return cls(**json_data)

    @classmethod
    def reset(cls) -> Self:
        """Write default config values to file.

        Returns:
            Config: default config instance
        """
        cls.clear_instances()
        instance = cls()
        cls.FILE_PATH.parent.mkdir(exist_ok=True)
        with cls.FILE_PATH.open("w") as config_file:
            json.dump(dataclasses.asdict(instance), config_file, indent=4)

        LOGGER.info("Config reset")

        return instance

    @classmethod
    def load(cls) -> Self:
        """Load config from FILE_PATH

        Returns:
            Config: new instance
        """
        if cls._instances:
            return cls()

        cls.FILE_PATH.parent.mkdir(exist_ok=True)
        if not cls.FILE_PATH.is_file():
            return cls.reset()

        return cls._load_from_json()

    @classmethod
    def save(cls):
        """Write config to json file."""
        instance = cls()
        cls.FILE_PATH.parent.mkdir(exist_ok=True)
        with cls.FILE_PATH.open("w") as config_file:
            json.dump(dataclasses.asdict(instance), config_file, indent=4)

        LOGGER.info(f"Saved config: {cls.FILE_PATH}")
